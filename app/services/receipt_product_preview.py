"""Bounded public product identity lookup, independent of price/stock parsers."""
import base64
import json
import re
from functools import lru_cache
from html.parser import HTMLParser
from io import BytesIO
from datetime import datetime, timezone
from decimal import Decimal
from urllib.parse import urljoin, urlsplit

import httpx
from PIL import Image, ImageOps

from app.services import retailer_price_provider as retailer


class ProductMissing(LookupError):
    pass


class Metadata(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.image = ''
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'meta' and a.get('property', a.get('name')) == 'og:image':
            self.image = a.get('content', '')


def product_image(html, url):
    meta = Metadata(html).image
    if meta:
        return meta
    for raw in re.findall(r'<script\b[^>]*type=[\"\']application/ld\+json[\"\'][^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(raw)
            for product in data if isinstance(data, list) else [data]:
                if not isinstance(product, dict) or product.get('@type') != 'Product':
                    continue
                if retailer.identify_url(product.get('url', '')) != retailer.identify_url(url):
                    continue
                image = product.get('image')
                return image[0] if isinstance(image, list) and image else image if isinstance(image, str) else ''
        except (ValueError, TypeError, AttributeError):
            continue
    return ''


def next_data(html):
    match = re.search(r'<script\b[^>]*\bid="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
    return json.loads(match[1])


def package_measurement(label, name, *, weighted=False):
    """Only one unambiguous package size; portions and multipacks need review."""
    if weighted:
        return None
    text = (str(label or '') + ' ' + str(name or '')).strip().lower()
    if re.search(r'\d\s*[xх×*]|[xх×*]\s*\d|\d\s*по\s*\d', text):
        return None
    matches = re.findall(r'(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(кг|мл|г|л|шт\.?)\b', text)
    units = {'кг': ('g', 1000), 'г': ('g', 1), 'л': ('ml', 1000), 'мл': ('ml', 1), 'шт': ('piece', 1)}
    sizes = set()
    for value, unit in matches:
        unit, scale = units[unit.rstrip('.')]
        amount = Decimal(value.replace(',', '.')) * scale
        if 0 < amount <= 1000000 and amount.as_tuple().exponent >= -3:
            sizes.add((amount, unit))
    if len(sizes) != 1:
        return None
    amount, unit = sizes.pop()
    return {'package_quantity': format(amount.normalize(), 'f'), 'package_unit': unit}


def price_preview(html, url, key):
    # Optional enrichment from the same HTML, with the price watcher's validated
    # unit/location/discount rules. Failed price parsing must not hide identity.
    try:
        parser = {'edostavka': retailer.edostavka_provider.parse_product,
                  'green': retailer.parse_green, 'sosedi': retailer.parse_sosedi}[key]
        snapshot = parser(html, url)
        if not snapshot.get('price'):
            return None
        return {field: snapshot.get(field) for field in
                ('price', 'regular_price', 'currency', 'unit', 'available', 'conditions')} | {
                    'checked_at': datetime.now(timezone.utc).isoformat()}
    except (ValueError, ArithmeticError):
        return None


def parse_product(html, url):
    key, url = retailer.identify_url(url)
    try:
        size_label, brand, image_value = '', '', product_image(html, url)
        weighted = False
        if key == 'edostavka':
            p = next_data(html)['props']['pageProps']['productData']['product']
            if str(p['productId']) != url.rsplit('/', 1)[-1]:
                raise ValueError('Wrong product')
            name, article, codes = p['productName'], str(p['productId']), []
            weighted = p.get('soldByWeight') is not False
            for group in p.get('additionalProperties', []):
                for prop in group.get('groupProperty', []):
                    units = {'Вес, гр': 'г', 'Вес, кг': 'кг', 'Объем, мл': 'мл', 'Объем, л': 'л'}
                    if prop.get('propertyName') in units:
                        value = prop.get('propertyValue', [])
                        value = value[0] if isinstance(value, list) and value else value
                        if isinstance(value, (str, int, float)):
                            size_label = (size_label + ' ' + str(value)[:30] + ' ' + units[prop['propertyName']]).strip()
                    if prop.get('propertyName') in ('Штрихкод', 'Штрих-код', 'EAN', 'GTIN'):
                        values = prop.get('propertyValue', [])
                        codes.extend(str(v) for v in (values if isinstance(values, list) else [values]))
        elif key == 'green':
            state = json.loads(next_data(html)['props']['initialState'])
            p = retailer.unpack(state['product'])['item']
            if p['slug'] != url.rstrip('/').rsplit('/', 1)[-1] or str(p['vendorCode']) != p['slug'].rsplit('-', 1)[-1]:
                raise ValueError('Wrong product')
            size_label = str(p.get('volume') or '')[:80]
            weighted = p.get('unit') != 'piece'
            brand = p.get('brand', {}).get('title', '') if isinstance(p.get('brand'), dict) else ''
            file = p.get('previewFile')
            if isinstance(file, dict):
                image_value = image_value or file.get('url') or file.get('path') or ''
            name, article, codes = p['title'], str(p['vendorCode']), [str(p.get('gtin') or '')]
        else:
            match = re.search(r'window\.SERVER_DATA\s*=\s*', html)
            p = json.JSONDecoder().raw_decode(html[match.end():])[0]['product']
            if p['slug'] != url.rsplit('/', 1)[-1] or str(p['id']) != p['slug'].rsplit('-', 1)[-1]:
                raise ValueError('Wrong product')
            brand = p.get('brand') if isinstance(p.get('brand'), str) else ''
            # Sosedi's public FILESTORAGE_URL serves the product's own img path.
            if isinstance(p.get('img'), str) and re.fullmatch(r'images/[a-zA-Z0-9_.-]+\.(?:jpg|jpeg|png|webp)', p['img']):
                image_value = image_value or 'https://bazar-store.by/' + p['img']
            name, article, codes = p['name'], str(p['id']), [str(p.get('cod') or '')]
            weighted = p.get('isWeightGoods') != 0
        if not isinstance(name, str) or not name.strip():
            raise ValueError('Missing name')
        return {'provider': key, 'source': retailer.PROVIDERS[key]['source'], 'url': url,
                'name': name[:320], 'size_label': size_label, 'brand': str(brand)[:120], 'image_url': safe_image_url(image_value, url),
                'measurement': package_measurement(size_label, name, weighted=weighted),
                'site_price': price_preview(html, url, key),
                'identifiers': {'article': article, 'barcodes': codes}}
    except (KeyError, TypeError, ValueError, IndexError, AttributeError) as exc:
        raise retailer.RetailerUnavailable('Не удалось прочитать карточку товара.') from exc


def fetch_product(url):
    _, url = retailer.identify_url(url)
    try:
        return parse_product(retailer.read_public(url), url)
    except (httpx.HTTPError, UnicodeError) as exc:
        if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code in (404, 410):
            raise ProductMissing('Страница товара отсутствует') from exc
        raise retailer.RetailerUnavailable('Сайт временно недоступен.') from exc


def search_products(key, query, kind):
    """Find bounded candidate URLs without requiring a valid price or stock field."""
    try:
        if key == 'edostavka':
            if kind == 'retailer':
                return [{'url': 'https://edostavka.by/product/' + query}] if re.fullmatch(r'[1-9][0-9]{0,9}', query) else []
            data = next_data(retailer.read_public('https://edostavka.by/search', {'query': query}))
            props = data['props']['pageProps']
            if data['page'] != '/search' or props['search']['query'] != query:
                raise ValueError('Wrong search')
            return [{'url': 'https://edostavka.by/product/' + str(i)} for i in props['search']['productIds'][:8]
                    if re.fullmatch(r'[1-9][0-9]{0,9}', str(i))]
        if key == 'green':
            data = next_data(retailer.read_public('https://green-dostavka.by/search/', {'search': query}))
            search = retailer.unpack(json.loads(data['props']['initialState'])['search'])
            if data['page'] != '/search' or search['searchValue'] != query:
                raise ValueError('Wrong search')
            products = search['products']
            if products['__iterable'] != 'List':
                raise ValueError('Wrong listing')
            result = []
            for entry in products['data']:
                p = retailer.unpack(entry)
                if kind == 'retailer' and str(p['vendorCode']) != query:
                    continue
                try:
                    _, url = retailer.identify_url('https://green-dostavka.by/product/' + p['slug'] + '/')
                except ValueError:
                    continue
                result.append({'url': url})
                if len(result) == 8:
                    break
            return result
        if key != 'sosedi':
            raise ValueError('Unsupported retailer')
        if kind == 'retailer':
            ids = [query] if re.fullmatch(r'[1-9][0-9]{0,11}', query) else []
        else:
            ids = retailer.parse_sosedi_search_ids(retailer.read_public('https://dev.bazar-store.by/v2/products/search', {'query': query}), query, kind)
        if not ids:
            return []
        index = retailer.sosedi_product_index()
        return [{'url': index[i]} for i in ids if i in index]
    except (KeyError, TypeError, ValueError, IndexError, httpx.HTTPError) as exc:
        raise retailer.RetailerUnavailable('Поиск на сайте не выполнен.') from exc


# Only known retailer media origins; never follow redirects or fetch arbitrary URLs.
IMAGE_HOSTS = frozenset({'edostavka.by', 'img.e-dostavka.by', 'static.e-dostavka.by',
    'cdn.ime.by', 'bazar-store.by', 'io.activecloud.com', 'green-dostavka.by', 'sosedi-dostavka.by'})


def safe_image_url(value, page_url):
    if not isinstance(value, str) or not value or len(value) > 2048:
        return None
    url = urljoin(page_url, value)
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return None
    if parts.scheme != 'https' or parts.hostname not in IMAGE_HOSTS or parts.username or parts.password or port not in (None, 443):
        return None
    return url


@lru_cache(maxsize=48)
def thumbnail(url, bucket):
    if not safe_image_url(url, url):
        raise ValueError('Unsupported image origin')
    with httpx.Client(timeout=5, follow_redirects=False, trust_env=False) as client:
        with client.stream('GET', url) as r:
            r.raise_for_status()
            body = bytearray()
            for chunk in r.iter_bytes():
                body.extend(chunk)
                if len(body) > 2_000_000:
                    raise ValueError('Image too large')
    try:
        decoded = Image.open(BytesIO(body))
    except Image.DecompressionBombError as exc:
        raise ValueError('Image too large') from exc
    with decoded as im:
        if im.width * im.height > 12_000_000 or im.format not in ('JPEG', 'PNG', 'WEBP'):
            raise ValueError('Unsupported image')
        im = ImageOps.exif_transpose(im)
        im.thumbnail((160, 160))
        output = BytesIO()
        im.convert('RGB').save(output, 'JPEG', quality=80)
    return 'data:image/jpeg;base64,' + base64.b64encode(output.getvalue()).decode()
