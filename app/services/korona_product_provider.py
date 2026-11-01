"""Public own-production catalogue. Names are suggestions, never code matches."""
import json
import math
import re
import time
from functools import lru_cache
from html.parser import HTMLParser
from urllib.parse import urlsplit

from app.services import retailer_price_provider as retailer
from app.services import receipt_product_preview as preview

ORIGIN = 'https://korona.by'
SLUG = r'[a-z0-9]+(?:-[a-z0-9]+)*'


def is_source(name):
    return str(name or '').strip().casefold() == 'корона'


def canonical_url(value):
    if not isinstance(value, str) or not re.fullmatch(re.escape(ORIGIN) + r'/our-production/' + SLUG + '/' + SLUG + '/?', value):
        raise ValueError('Нужна ссылка на карточку продукции Короны')
    return value.rstrip('/')


class PlainText(HTMLParser):
    def __init__(self, value):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.feed(str(value or ''))

    def handle_data(self, value):
        self.parts.append(value)


def snapshot(product):
    if not isinstance(product, dict):
        raise ValueError('Некорректная карточка Короны')
    name = str(product['name']).strip()
    category = product['category_url_alias']
    alias = product.get('product_url_alias') or product['url_alias']
    url = canonical_url(f'{ORIGIN}/our-production/{category}/{alias}')
    if not name or len(name) > 320:
        raise ValueError('Некорректная карточка Короны')
    image = product.get('image') or {}
    thumbnails = image.get('thumbnails') if isinstance(image, dict) else None
    image = ((thumbnails.get('url') if isinstance(thumbnails, dict) else None) or image.get('url')) if isinstance(image, dict) else None
    image = preview.safe_image_url(image, url)
    # Nutrition values and ingredient quantities are not package dimensions.
    size_text = name + ' ' + str(product.get('caption') or '')
    measurement = preview.package_measurement('', size_text, weighted=bool(re.search(r'\b(?:весов\w*|на вес)\b', size_text, re.I)))
    return {'name': name, 'url': url, 'source': 'Корона', 'image_url': image,
            'description': ' '.join(PlainText(product.get('composition')).parts)[:320],
            'measurement': measurement, 'size_label': size_text if measurement else '',
            'site_price': None, 'price_unpublished': True, 'matched_by': 'name',
            'requires_confirmation': True}


@lru_cache(maxsize=2)
def catalogue(bucket):
    data = json.loads(retailer.read_public(ORIGIN + '/api/our-production/products'))['data']
    if not isinstance(data, list) or len(data) > 2000:
        raise ValueError('Некорректный каталог Короны')
    result = []
    for product in data:
        if not isinstance(product, dict) or product.get('is_disabled'):
            continue
        try:
            result.append(snapshot(product))
        except (KeyError, TypeError, ValueError):
            continue
    if data and not result:
        raise ValueError('Не удалось прочитать каталог Короны')
    return result


def words(value):
    tokens = re.findall(r'[a-zа-яё]+', str(value).casefold().replace('ё', 'е'))
    stop = {'с', 's', 'в', 'и', 'из', 'для', 'на', 'по', 'г', 'кг', 'мл', 'л', 'шт', 'вес', 'охл', 'зам', 'пк', 'корона'}
    return {re.sub(r'(?:ами|ями|ого|ому|ая|ое|ые|ий|ый|ой|ом|ов|ам|ах|ях|а|я|ы|и|у|ю|е)$', '', token) if len(token) > 4 else token
            for token in tokens if token not in stop and len(token) >= 2}


def search(name, *, refresh=False):
    query = words(name)
    if not query:
        return []
    products = (catalogue.__wrapped__ if refresh else catalogue)(int(time.time() // 21600))
    ranked = []
    for product in products:
        candidate = words(product['name'])
        overlap = len(query & candidate)
        if overlap >= (1 if len(query) == 1 else max(2, math.ceil(len(query) * .6))):
            ranked.append((overlap / len(query), overlap / max(1, len(candidate)), product))
    ranked.sort(key=lambda row: (-row[0], -row[1], row[2]['name']))
    return [dict(row[2]) for row in ranked[:8]]


def fetch_product(url):
    url = canonical_url(url)
    alias = urlsplit(url).path.rsplit('/', 1)[-1]
    data = json.loads(retailer.read_public(ORIGIN + '/api/our-production/product/' + alias))['data']
    result = snapshot(data)
    if result['url'] != url:
        raise ValueError('Карточка Короны изменилась')
    return result
