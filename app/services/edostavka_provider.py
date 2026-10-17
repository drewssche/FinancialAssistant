"""Read public product cards only; never trust arbitrary user-supplied fetch URLs."""
import json
import re
from decimal import Decimal, InvalidOperation
import httpx


class RetailerUnavailable(ValueError):
    pass


def canonical_url(value: str) -> str:
    match = re.fullmatch(r'https://(?:www\.)?edostavka\.by/product/([1-9][0-9]{0,9})/?(?:\?[^#\s]*)?(?:#[^\s]*)?', value.strip())
    if not match:
        raise ValueError('Нужна ссылка на товар https://edostavka.by/product/…')
    return f'https://edostavka.by/product/{match[1]}'


def parse_product(html: str, url: str) -> dict:
    try:
        match = re.search(r'<script\b[^>]*\bid="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        p = json.loads(match[1])['props']['pageProps']['productData']['product']
        if str(p['productId']) != url.rsplit('/', 1)[-1]:
            raise ValueError('Wrong product')
        price = Decimal(str(p['price']['discountedPrice']))
        regular = Decimal(str(p['price']['basePrice']))
        available = p['restInformation']['isAvailable']
        if not isinstance(available, bool):
            raise ValueError('Unknown availability')
        if not price.is_finite() or not regular.is_finite():
            raise ValueError('Invalid price')
        # Out-of-stock cards stay addressable by article, but publish zero as
        # a placeholder. It is missing price evidence, never a free product.
        missing_price = not available and price == regular == 0
        if not missing_price and not 0 < price <= regular < 1000000:
            raise ValueError('Invalid price')
        size = []
        barcodes = []
        for group in p.get('additionalProperties', []):
            for prop in group.get('groupProperty', []):
                if prop.get('propertyName') in ('Штрихкод', 'Штрих-код', 'EAN', 'GTIN'):
                    values = prop.get('propertyValue', [])
                    barcodes.extend(str(v) for v in (values if isinstance(values, list) else [values]))
                if prop.get('propertyName') in ('Вес, гр', 'Объем, л', 'Объем, мл', 'Вес, кг'):
                    size.append([prop['propertyName'], prop['propertyValue']])
        measure = str(p['quantityInfo']['measure'])
        conditions = 'Публичная цена сайта; адрес доставки не выбран. Условия акции уточняйте в магазине.'
        if p.get('optDiscounts') or p.get('messages'):
            conditions += ' Есть дополнительные условия/предложения на странице.'
        return {'provider': 'edostavka', 'source': 'Е-доставка', 'url': url,
                'name': str(p['productName'])[:320], 'price': None if missing_price else str(price),
                'regular_price': None if missing_price else str(regular),
                'currency': 'BYN', 'available': available, 'unit': measure,
                'identifiers': {'article': str(p['productId']), 'barcodes': barcodes},
                'conditions_key': json.dumps([p.get('optDiscounts', []), p.get('messages', [])], ensure_ascii=False, sort_keys=True),
                'size': size, 'comparison_key': json.dumps([url, measure, p.get('soldByWeight'), size], ensure_ascii=False, sort_keys=True),
                'normalized': str(p['price'].get('measurePrice') or '')[:160], 'conditions': conditions}
    except (KeyError, TypeError, ValueError, IndexError, InvalidOperation) as exc:
        raise RetailerUnavailable('Не удалось прочитать цену и фасовку. Сохранена последняя успешная проверка.') from exc


def fetch_product(value: str) -> dict:
    url = canonical_url(value)
    try:
        # No redirects: a retailer response cannot cause a request to a private host.
        with httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client:
            with client.stream('GET', url, headers={'User-Agent': 'FinancialAssistant price watch/1.0'}) as response:
                response.raise_for_status()
                parts = bytearray()
                for part in response.iter_bytes():
                    parts.extend(part)
                    if len(parts) > 3_000_000:
                        raise ValueError('Page too large')
        return parse_product(parts.decode('utf-8'), url)
    except (httpx.HTTPError, UnicodeError, ValueError) as exc:
        raise RetailerUnavailable('Е-доставка временно недоступна или изменила карточку. Повторим проверку позже.') from exc


def parse_search(html: str, query: str) -> list[dict]:
    """Search hits are candidates, never proof of barcode identity."""
    try:
        match = re.search(r'<script\b[^>]*\bid="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
        data = json.loads(match[1])
        props = data['props']['pageProps']
        if data['page'] != '/search' or props['search']['query'] != query:
            raise ValueError('Unexpected search page')
        raw_ids = props['search']['productIds']
        products = props['listing']['products']
        if not isinstance(raw_ids, list) or not isinstance(products, list):
            raise ValueError('Invalid listing')
        ids = {str(i) for i in raw_ids}
        result = []
        for p in products:
            if not isinstance(p, dict):
                raise ValueError('Invalid product')
            product_id = str(p.get('productId', ''))
            # Exclude recommendations and construct URLs ourselves.
            if product_id not in ids or not re.fullmatch(r'[1-9][0-9]{0,9}', product_id):
                continue
            price = Decimal(str(p['price']['discountedPrice']))
            if not price.is_finite() or not 0 < price < 1000000:
                continue
            result.append({'url': f'https://edostavka.by/product/{product_id}',
                           'name': str(p['productName'])[:320], 'price': str(price),
                           'unit': str(p['quantityInfo']['measure'])[:30],
                           'available': p['restInformation']['isAvailable'] is True,
                           'article': product_id})
            if len(result) == 8:
                break
        return result
    except (KeyError, TypeError, ValueError, IndexError, InvalidOperation) as exc:
        raise RetailerUnavailable('Не удалось прочитать результаты поиска Е-доставки.') from exc


def search_products(query: str, kind: str = 'name') -> list[dict]:
    query = query.strip()
    if not 2 <= len(query) <= 160 or any(ord(c) < 32 for c in query):
        raise ValueError('Введите от 2 до 160 символов для поиска.')
    if kind == 'retailer':
        # The article is the product ID; site search excludes some unavailable
        # products. Read the exact card and verify its ID in parse_product.
        if not re.fullmatch(r'[1-9][0-9]{0,9}', query):
            return []
        try:
            product = fetch_product(f'https://edostavka.by/product/{query}')
        except RetailerUnavailable as exc:
            cause = exc.__cause__
            if isinstance(cause, httpx.HTTPStatusError) and cause.response.status_code in (404, 410):
                return []
            raise
        return [{key: product[key] for key in ('url', 'name', 'price', 'unit', 'available')} |
                {'article': product['identifiers']['article']}]
    try:
        with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client:
            with client.stream('GET', 'https://edostavka.by/search', params={'query': query},
                               headers={'User-Agent': 'FinancialAssistant price watch/1.0'}) as response:
                response.raise_for_status()
                parts = bytearray()
                for part in response.iter_bytes():
                    parts.extend(part)
                    if len(parts) > 3_000_000:
                        raise ValueError('Page too large')
        return parse_search(parts.decode('utf-8'), query)
    except (httpx.HTTPError, UnicodeError, ValueError) as exc:
        raise RetailerUnavailable('Поиск Е-доставки временно недоступен. Повторите позже.') from exc
