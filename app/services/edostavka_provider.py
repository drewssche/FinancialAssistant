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
        if not price.is_finite() or not regular.is_finite() or not 0 < price <= regular < 1000000:
            raise ValueError('Invalid price')
        available = p['restInformation']['isAvailable']
        if not isinstance(available, bool):
            raise ValueError('Unknown availability')
        size = []
        for group in p.get('additionalProperties', []):
            for prop in group.get('groupProperty', []):
                if prop.get('propertyName') in ('Вес, гр', 'Объем, л', 'Объем, мл', 'Вес, кг'):
                    size.append([prop['propertyName'], prop['propertyValue']])
        measure = str(p['quantityInfo']['measure'])
        conditions = 'Публичная цена сайта; адрес доставки не выбран. Условия акции уточняйте в магазине.'
        if p.get('optDiscounts') or p.get('messages'):
            conditions += ' Есть дополнительные условия/предложения на странице.'
        return {'provider': 'edostavka', 'source': 'Е-доставка', 'url': url,
                'name': str(p['productName'])[:320], 'price': str(price), 'regular_price': str(regular),
                'currency': 'BYN', 'available': available, 'unit': measure,
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
