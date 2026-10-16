"""Public retailer prices. No account cookies, redirects or arbitrary fetch hosts."""
import json
import re
from decimal import Decimal
from urllib.parse import unquote

import httpx

from app.services import edostavka_provider
from app.services.edostavka_provider import RetailerUnavailable

PROVIDERS = {
    'edostavka': {'source': 'Е-доставка', 'example_url': 'https://edostavka.by/product/…', 'search': True},
    'green': {'source': 'Green', 'example_url': 'https://green-dostavka.by/product/…', 'search': True},
    'sosedi': {'source': 'Соседи', 'example_url': 'https://sosedi-dostavka.by/products/…', 'search': True},
}
ALIASES = {
    'edostavka': {'едоставка', 'евроопт', 'edostavka', 'edostavkaby', 'euroopt'},
    'green': {'green', 'грин', 'greendostavka', 'гриндоставка'},
    'sosedi': {'соседи', 'соседидоставка', 'sosedi', 'sosedidostavka'},
}


def source_provider(name):
    normalized = re.sub(r'[^a-zа-яё]', '', (name or '').lower())
    return next((key for key, names in ALIASES.items() if normalized in names), None)


def identify_url(value):
    value = unquote(value.strip())
    for key, host, path in [('green', 'green-dostavka.by', 'product'), ('sosedi', 'sosedi-dostavka.by', 'products')]:
        match = re.fullmatch(r'https://' + re.escape(host) + '/' + path + r'/([a-zа-яё0-9№]+(?:[.-][a-zа-яё0-9№]+)*-[1-9][0-9]{0,11})/?(?:\?[^#\s]*)?(?:#[^\s]*)?', value)
        if match:
            return key, f'https://{host}/{path}/{match[1]}' + ('/' if key == 'green' else '')
    try:
        return 'edostavka', edostavka_provider.canonical_url(value)
    except ValueError:
        raise ValueError('Нужна ссылка на товар Е-доставки, Green или Соседей.') from None


def number(value, *, positive=False, signed=False):
    if isinstance(value, bool):
        raise ValueError('Invalid number')
    result = Decimal(str(value))
    if not result.is_finite() or (not signed and result < 0) or abs(result) >= 10000000 or (positive and result == 0):
        raise ValueError('Invalid number')
    return result


def unpack(value):
    if isinstance(value, dict) and value.get('__iterable') == 'Map':
        return dict(value['data'])
    raise ValueError('Unexpected state')


def snapshot(provider, url, name, price, regular, available, unit, size, identity, store_id, store_name, normalized='', extra=''):
    if not isinstance(name, str) or not name.strip() or not Decimal("0.01") <= price <= regular < 1000000:
        raise ValueError('Invalid product/price')
    if not store_id or not store_name:
        raise ValueError('Unknown price location')
    return {'provider': provider, 'source': PROVIDERS[provider]['source'], 'url': url,
            'name': name[:320], 'price': format(price, '.2f'), 'regular_price': format(regular, '.2f'),
            'currency': 'BYN', 'available': available, 'unit': unit, 'size': size,
            'comparison_key': json.dumps([url, identity, unit, size, store_id, 'BYN'], ensure_ascii=False, sort_keys=True),
            'conditions_key': f'{provider}:public:store:{store_id}',
            'normalized': normalized,
            'conditions': f'Публичная цена сайта · {str(store_name)[:100]}. Адрес доставки не выбран. {extra}'.strip()}


def parse_green(html, url):
    try:
        match = re.search(r'<script\b[^>]*\bid="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        state = json.loads(json.loads(match[1])['props']['initialState'])
        product = unpack(state['product'])
        p, offer = product['item'], product['storeProduct']
        slug = url.rstrip('/').rsplit('/', 1)[1]
        if p['slug'] != slug or str(p['vendorCode']) != slug.rsplit('-', 1)[1] or p['id'] != offer['productId']:
            raise ValueError('Wrong product')
        if p['unit'] not in ('piece', 'weight') or not isinstance(offer['isActive'], bool):
            raise ValueError('Unknown unit/availability')
        price = number(offer['priceWithSale'], positive=True) / 100
        regular = number(offer['price'], positive=True) / 100
        store_id = offer['storeId']
        store = unpack(unpack(unpack(state['store'])['stores'])[str(store_id)])
        size = [str(p.get('volume') or ''), p.get('altUnit'), p.get('measur')]
        unit = 'кг' if p['unit'] == 'weight' else 'шт.'
        return snapshot('green', url, p['title'], price, regular,
                        offer['isActive'] and number(offer['balance'], signed=True) > 0, unit, size,
                        [p['id'], p.get('gtin'), p['unit']], store_id,
                        store.get('additionalAddressInfo') or store['name'],
                        normalized=str(p.get('volume') or '')[:160],
                        extra='Скидка по карте и кешбэк не включены.') | {'identifiers': {'article': str(p['vendorCode']), 'barcodes': [str(p.get('gtin') or '')]}}
    except (KeyError, TypeError, ValueError, IndexError, ArithmeticError) as exc:
        raise RetailerUnavailable('Green: не удалось проверить цену, фасовку и наличие. Последняя цена сохранена.') from exc


def parse_sosedi(html, url):
    try:
        match = re.search(r'window\.SERVER_DATA\s*=\s*', html)
        data = json.JSONDecoder().raw_decode(html[match.end():])[0]
        p, store = data['product'], data['darkstore']
        slug = url.rsplit('/', 1)[1]
        if p['slug'] != slug or str(p['id']) != slug.rsplit('-', 1)[1] or p['currencyISO'] != 'BYN':
            raise ValueError('Wrong product/currency')
        if p['isWeightGoods'] not in (0, 1) or p['status'] not in (0, 1) or p['isWait'] not in (0, 1):
            raise ValueError('Unknown availability')
        regular = number(p['price'], positive=True)
        discounted = number(p['priceDiscount']) if p['priceDiscount'] is not None else Decimal(0)
        price = discounted if 0 < discounted < regular else regular
        weight = number(p['weight'])
        # The site's currentPrice is the price of the displayed portion, not per kg.
        # Keep that basis exactly; pricePerKg is the regular price, even during sales.
        if p['isWeightGoods'] and weight <= 0:
            raise ValueError('Unknown portion')
        unit = f'{format(weight.normalize(), "f").replace(".", ",")} кг' if p['isWeightGoods'] else 'шт.'
        size = [str(weight), p['liter'], p['isWeightGoods'], p.get('servingWeight'), p.get('maxServingWeight')]
        return snapshot('sosedi', url, p['name'], price, regular,
                        p['status'] == 1 and not p['isWait'] and number(p['qty'], signed=True) > 0,
                        unit, size, [p['id'], p.get('cod'), p['name']], store['id'], store['name']) | {'identifiers': {'article': str(p['id']), 'barcodes': [str(p.get('cod') or '')]}}
    except (KeyError, TypeError, ValueError, IndexError, AttributeError, ArithmeticError) as exc:
        raise RetailerUnavailable('Соседи: не удалось проверить цену, фасовку и наличие. Последняя цена сохранена.') from exc


def fetch_product(value):
    provider, url = identify_url(value)
    if provider == 'edostavka':
        return edostavka_provider.fetch_product(url)
    try:
        with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
            with client.stream('GET', url, headers={'User-Agent': 'FinancialAssistant price watch/1.0'}) as response:
                response.raise_for_status()
                body = bytearray()
                for part in response.iter_bytes():
                    body.extend(part)
                    if len(body) > 3_000_000:
                        raise ValueError('Page too large')
        return (parse_green if provider == 'green' else parse_sosedi)(body.decode('utf-8'), url)
    except (httpx.HTTPError, UnicodeError, ValueError) as exc:
        raise RetailerUnavailable(f'{PROVIDERS[provider]["source"]}: сайт временно недоступен или изменил карточку. Повторим позже.') from exc


def parse_green_search(html, query, kind):
    """Only the requested search listing; recommended products are never candidates."""
    try:
        match = re.search(r'<script\b[^>]*\bid="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        data = json.loads(match[1])
        search = unpack(json.loads(data['props']['initialState'])['search'])
        if data['page'] != '/search' or search['searchValue'] != query:
            raise ValueError('Unexpected search')
        products = search['products']
        if products['__iterable'] != 'List' or not isinstance(products['data'], list):
            raise ValueError('Unexpected listing')
        result = []
        for entry in products['data']:
            p = unpack(entry)
            if kind == 'retailer' and str(p['vendorCode']) != query:
                continue
            try:
                _, url = identify_url('https://green-dostavka.by/product/' + p['slug'] + '/')
            except ValueError:
                continue
            offer = unpack(p['storeProduct'])
            price = number(offer['priceWithSale'], positive=True) / 100
            if p['unit'] not in ('piece', 'weight') or not isinstance(offer['isActive'], bool):
                raise ValueError('Unknown unit/availability')
            result.append({'url': url, 'name': str(p['title'])[:320], 'price': format(price, '.2f'),
                           'unit': 'кг' if p['unit'] == 'weight' else 'шт.',
                           'available': offer['isActive'] and number(offer['balance'], signed=True) > 0,
                           'article': str(p['vendorCode'])})
            if len(result) == 8:
                break
        return result
    except (KeyError, TypeError, ValueError, IndexError, ArithmeticError) as exc:
        raise RetailerUnavailable('Не удалось прочитать результаты поиска Green.') from exc


def read_public(url, params=None):
    # Callers construct fixed, public retailer URLs. Queries are always encoded separately.
    with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
        with client.stream('GET', url, params=params, headers={'User-Agent': 'FinancialAssistant price watch/1.0'}) as response:
            response.raise_for_status()
            body = bytearray()
            for part in response.iter_bytes():
                body.extend(part)
                if len(body) > 3_000_000:
                    raise ValueError('Response too large')
    return body.decode('utf-8')


def search_products(provider, query, kind='name'):
    query = query.strip()
    if not 2 <= len(query) <= 160 or any(ord(c) < 32 for c in query):
        raise ValueError('Введите от 2 до 160 символов для поиска.')
    if provider not in PROVIDERS or kind not in ('name', 'barcode', 'retailer'):
        raise ValueError('Неизвестный источник или тип кода.')
    if provider == 'edostavka':
        return edostavka_provider.search_products(query)
    try:
        if provider == 'green':
            return parse_green_search(read_public('https://green-dostavka.by/search/', {'search': query}), query, kind)
        return search_sosedi(query, kind)
    except (httpx.HTTPError, UnicodeError, ValueError) as exc:
        raise RetailerUnavailable(f'Поиск {PROVIDERS[provider]["source"]} временно недоступен. Повторите позже.') from exc


def parse_sosedi_search_ids(body, query, kind):
    try:
        rows = json.loads(body)['data']
        if not isinstance(rows, list):
            raise ValueError('Unexpected listing')
        ids = []
        for row in rows:
            identity = str(row['id'])
            if not re.fullmatch(r'[1-9][0-9]{0,11}', identity):
                continue
            # The search index also returns fuzzy recommendations for a barcode.
            if kind == 'barcode' and not any(token.zfill(14) == query.zfill(14) for token in re.findall(r'(?<!\d)\d{8,14}(?!\d)', row['name'])):
                continue
            if identity not in ids:
                ids.append(identity)
        return ids[:3]
    except (KeyError, TypeError, ValueError) as exc:
        raise RetailerUnavailable('Не удалось прочитать результаты поиска Соседей.') from exc


def sosedi_product_index():
    # The public search API returns IDs, not URLs; resolve them through the retailer's sitemap.
    # Keep a bounded public index in the shared cache, without any user catalog data.
    from app.core.cache import get_json, set_json
    import xml.etree.ElementTree as ET
    key = 'public:sosedi:product-urls:v1'
    cached = get_json(key)
    if isinstance(cached, dict) and cached:
        return cached
    try:
        root = ET.fromstring(read_public('https://sosedi-dostavka.by/sitemap.xml'))
    except ET.ParseError as exc:
        raise RetailerUnavailable('Не удалось прочитать каталог Соседей.') from exc
    result = {}
    for loc in root.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc'):
        try:
            retailer, url = identify_url(loc.text or '')
        except ValueError:
            continue
        if retailer == 'sosedi':
            result[url.rsplit('-', 1)[-1]] = url
    if not result:
        raise RetailerUnavailable('Не удалось прочитать каталог Соседей.')
    set_json(key, result, ttl_seconds=21600)
    return result


def search_sosedi(query, kind):
    if kind == 'retailer':
        # Site article is the numeric ID. Do not guess another product from a fuzzy code.
        if not re.fullmatch(r'[1-9][0-9]{0,11}', query):
            return []
        ids = [query]
    else:
        ids = parse_sosedi_search_ids(read_public('https://dev.bazar-store.by/v2/products/search', {'query': query}), query, kind)
    if not ids:
        return []
    index = sosedi_product_index()
    result = []
    for identity in ids:
        value = index.get(identity)
        if not value:
            continue
        retailer, url = identify_url(value)
        if retailer != 'sosedi' or url.rsplit('-', 1)[-1] != identity:
            raise ValueError('Unexpected product URL')
        html = read_public(url)
        match = re.search(r'window\.SERVER_DATA\s*=\s*', html)
        try:
            product = json.JSONDecoder().raw_decode(html[match.end():])[0]['product']
            if kind == 'barcode' and str(product.get('cod', '')).zfill(14) != query.zfill(14):
                continue
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise RetailerUnavailable('Не удалось подтвердить код товара Соседей.') from exc
        s = parse_sosedi(html, url)
        result.append({key: s[key] for key in ('url', 'name', 'price', 'unit', 'available')} | {'article': identity})
    return result
