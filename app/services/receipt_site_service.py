"""Read-only receipt discovery; verified selections join the operation transaction."""
import hashlib
import hmac
import time
from datetime import timedelta
from functools import lru_cache

from jose import JWTError, jwt

from app.core.config import get_settings
from app.db.models.catalog_identity import CatalogOfferIdentity
from app.db.models.catalog_watch import CatalogOfferWatch
from app.services import retailer_price_provider as provider
from app.services.catalog_match_service import barcodes
from app.services.catalog_watch_service import CatalogWatchService, now
from app.services.item_source_service import ItemSourceService
from app.services.receipt_code_service import variable_code


def signing_key():
    # A receipt selection must never be usable as an API access token.
    return hmac.new(get_settings().app_secret_key.encode(), b'receipt-site-selection-v1', hashlib.sha256).hexdigest()


def code_context(codes):
    result = set()
    for entry in codes:
        code = entry['code'].strip()
        if not code:
            continue
        kind = entry['kind']
        canonical = barcodes([code]) if kind in ('barcode', 'unknown') else set()
        if kind == 'barcode' and not canonical:
            raise ValueError('Проверьте контрольную цифру штрихкода')
        result.add(('barcode', next(iter(canonical))) if canonical else ('retailer', code))
    return sorted(result)


@lru_cache(maxsize=128)
def discover(key, queries, bucket):
    """Short bounded cache contains public retailer data only, never account data."""
    hits, exact, incomplete = {}, [], len(queries) > 3
    for kind, code in queries[:3]:
        # GTIN-14 normalization is for comparison; sites usually search EAN-13.
        query = code[1:] if kind == 'barcode' and len(code) == 14 and code.startswith('0') else code
        found = provider.search_products(key, query, kind)
        incomplete |= len(found) >= (3 if key == 'sosedi' else 8)
        for hit in found:
            actual_key, url = provider.identify_url(hit['url'])
            if actual_key != key:
                raise ValueError('Сайт результата не соответствует источнику')
            hits[url] = hit
    requested_barcodes = {code for kind, code in queries if kind == 'barcode'}
    articles = {code for kind, code in queries if kind == 'retailer'}
    incomplete |= len(hits) > 8 or any(variable_code(c) for c in requested_barcodes)
    for url in list(hits)[:8]:
        snapshot = provider.fetch_product(url)
        actual_key, actual_url = provider.identify_url(snapshot['url'])
        if actual_key != key or actual_url != url:
            raise ValueError('Карточка сайта не соответствует результату поиска')
        ids = snapshot.get('identifiers', {})
        actual_barcodes = barcodes(ids.get('barcodes', []))
        barcode_match = bool(requested_barcodes & actual_barcodes)
        article_match = str(ids.get('article') or '') in articles
        conflict = bool(requested_barcodes and actual_barcodes and not barcode_match)
        incomplete |= conflict or bool(articles and ids.get('article') and not article_match)
        if (barcode_match or article_match) and not conflict:
            exact.append(snapshot)
    return exact, incomplete


class ReceiptSiteService:
    def __init__(self, db):
        self.db = db

    def lookup(self, *, user_id, codes, shop_name='', source_id=None):
        if source_id:
            shop_name = ItemSourceService(self.db).get(user_id=user_id, source_id=source_id)['name']
        key = provider.source_provider(shop_name)
        if not key:
            return {'items': [], 'auto_match': False, 'state': 'unsupported'}
        context = code_context(codes)
        if not context:
            return {'items': [], 'auto_match': False, 'state': 'missing_codes'}
        try:
            snapshots, incomplete = discover(key, tuple(context), int(time.time() // 300))
        except (ValueError, LookupError):
            return {'items': [], 'auto_match': False, 'state': 'unavailable'}
        items = []
        for snapshot in snapshots:
            selection = jwt.encode({'user_id': user_id, 'provider': key, 'codes': context,
                                    'snapshot': snapshot, 'exp': now() + timedelta(days=7)}, signing_key(), algorithm='HS256')
            items.append({'name': snapshot['name'], 'url': snapshot['url'], 'site_selection': selection})
        return {'items': items, 'auto_match': len(items) == 1 and not incomplete,
                'state': 'found' if items else 'not_found', 'source': provider.PROVIDERS[key]['source']}

    def attach(self, *, user_id, template, item):
        try:
            chosen = jwt.decode(item['site_selection'], signing_key(), algorithms=['HS256'])
        except JWTError as exc:
            raise ValueError('Выбор товара на сайте устарел. Откройте чек и повторите поиск по кодам.') from exc
        key = CatalogWatchService(self.db).provider(template)
        context = code_context(item.get('catalog_codes') or [])
        if chosen.get('user_id') != user_id or chosen.get('provider') != key or chosen.get('codes') != [list(c) for c in context]:
            raise ValueError('Магазин или коды изменились. Повторите поиск товара на сайте в чеке.')
        snapshot = chosen['snapshot']
        provider_key, url = provider.identify_url(snapshot['url'])
        if provider_key != key:
            raise ValueError('Сайт товара не соответствует магазину')
        identity = self.db.get(CatalogOfferIdentity, template.id)
        if identity is None:
            identity = CatalogOfferIdentity(template_id=template.id, user_id=user_id, variant_id=item.get('variant_id'))
            self.db.add(identity)
        if identity.product_url and provider.identify_url(identity.product_url)[1] != url:
            raise ValueError('У предложения уже другая ссылка. Измените её в карточке товара.')
        identity.product_url, identity.external_name = url, snapshot['name']
        watch = self.db.get(CatalogOfferWatch, template.id)
        if watch and watch.url != url:
            raise ValueError('У предложения уже отслеживается другая страница магазина.')
        if watch is None:
            # Discovery snapshots can be old after a long review; schedule a fresh observation.
            watch = CatalogOfferWatch(template_id=template.id, user_id=user_id, product_id=template.product_id,
                                      url=url, snapshot={}, next_check_at=now())
            self.db.add(watch)
        # No receipt/template price changes, no commits, no notification on linking.
