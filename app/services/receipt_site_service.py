"""Read-only receipt discovery; verified selections join the operation transaction."""
import hashlib
import hmac
import time
import httpx
from datetime import timedelta
from functools import lru_cache

from jose import JWTError, jwt

from app.core.config import get_settings
from app.db.models.catalog_identity import CatalogOfferIdentity
from app.db.models.catalog_watch import CatalogOfferWatch
from app.services import retailer_price_provider as provider
from app.services import receipt_product_preview as preview
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
        # Internal store labels are not a website's stable SKU or global GTIN.
        if kind == 'internal' or variable_code(code):
            continue
        canonical = barcodes([code]) if kind in ('barcode', 'unknown') else set()
        if kind == 'barcode' and not canonical:
            raise ValueError('Проверьте контрольную цифру штрихкода')
        result.add(('barcode', next(iter(canonical))) if canonical else ('retailer', code))
    return sorted(result)


@lru_cache(maxsize=128)
def discover(key, queries, bucket, saved_url=None):
    """Short bounded cache contains public retailer data only, never account data."""
    hits, exact, incomplete = {}, [], len(queries) > 3
    requested_barcodes = {code for kind, code in queries if kind == 'barcode'}
    articles = {code for kind, code in queries if kind == 'retailer'}

    def verify(url):
        actual_key, url = provider.identify_url(url)
        if actual_key != key:
            raise ValueError('Сайт результата не соответствует источнику')
        snapshot = preview.fetch_product(url)
        if provider.identify_url(snapshot['url']) != (key, url):
            raise ValueError('Карточка сайта не соответствует результату поиска')
        ids = snapshot.get('identifiers', {})
        actual_barcodes = barcodes(ids.get('barcodes', []))
        barcode_match = bool(requested_barcodes & actual_barcodes)
        article_match = str(ids.get('article') or '') in articles
        conflict = bool(requested_barcodes and actual_barcodes and not barcode_match)
        ambiguous = conflict or bool(articles and ids.get('article') and not article_match)
        if (barcode_match or article_match) and not conflict:
            snapshot['code_warning'] = 'Артикул на сайте отличается от артикула в чеке' if articles and not article_match else ''
            snapshot['matched_by'] = 'barcode' if barcode_match else 'retailer'
            snapshot['matched_code'] = next(iter(sorted(requested_barcodes & actual_barcodes))) if barcode_match else str(ids['article'])
            return snapshot, ambiguous
        return None, ambiguous

    if saved_url:
        try:
            snapshot, ambiguous = verify(saved_url)
            if snapshot and not ambiguous:
                return [snapshot], False
        except (ValueError, LookupError, OSError):
            pass
    for kind, code in queries[:3]:
        query = code[1:] if kind == 'barcode' and len(code) == 14 and code.startswith('0') else code
        try:
            found = preview.search_products(key, query, kind)
        except (ValueError, LookupError, OSError):
            incomplete = True
            continue
        incomplete |= len(found) >= (3 if key == 'sosedi' else 8)
        for hit in found:
            actual_key, url = provider.identify_url(hit['url'])
            if actual_key != key:
                raise ValueError('Сайт результата не соответствует источнику')
            hits[url] = hit
    if not hits and incomplete:
        raise ValueError('Поиск сайта не завершён')
    incomplete |= len(hits) > 8
    failed = 0
    for url in list(hits)[:8]:
        try:
            snapshot, ambiguous = verify(url)
            incomplete |= ambiguous
            if snapshot:
                exact.append(snapshot)
        except preview.ProductMissing:
            continue
        except (ValueError, LookupError, OSError):
            failed += 1
            incomplete = True
    if hits and failed == min(len(hits), 8):
        raise ValueError('Карточки сайта не удалось проверить')
    return exact, incomplete


class ReceiptSiteService:
    def __init__(self, db):
        self.db = db

    def lookup(self, *, user_id, codes, shop_name='', source_id=None, template_id=None, other_sources=False):
        if source_id:
            shop_name = ItemSourceService(self.db).get(user_id=user_id, source_id=source_id)['name']
        key = provider.source_provider(shop_name)
        context = code_context(codes)
        if other_sources:
            # A store SKU/internal label has no meaning at another retailer.
            context = [(kind, code) for kind, code in context if kind == 'barcode']
        if not context:
            return {'items': [], 'auto_match': False, 'state': 'missing_codes'}
        if not key and not other_sources:
            return {'items': [], 'auto_match': False, 'state': 'unsupported'}
        saved_url = None
        if template_id:
            identity = self.db.get(CatalogOfferIdentity, template_id)
            if identity and identity.user_id != user_id:
                raise LookupError('Предложение не найдено')
            if identity and identity.product_url:
                try:
                    saved_key, url = provider.identify_url(identity.product_url)
                    if saved_key == key:
                        saved_url = url
                except ValueError:
                    pass
        keys = [k for k in provider.PROVIDERS if k != key] if other_sources else [key]
        items, incomplete, failures = [], False, 0
        for search_key in keys:
            try:
                snapshots, partial = discover(search_key, tuple(context), int(time.time() // 300), saved_url if search_key == key else None)
                incomplete |= partial
            except (ValueError, LookupError, OSError):
                failures += 1
                incomplete = True
                continue
            for snapshot in snapshots:
                # The signed selection is small; images are fetched separately on demand.
                selection = None if other_sources else jwt.encode({'user_id': user_id, 'provider': key, 'codes': context,
                    'snapshot': snapshot, 'exp': now() + timedelta(days=7)}, signing_key(), algorithm='HS256')
                image_token = jwt.encode({'user_id': user_id, 'purpose': 'receipt-thumbnail', 'url': snapshot['image_url'],
                    'exp': now() + timedelta(hours=1)}, signing_key(), algorithm='HS256') if snapshot.get('image_url') else None
                items.append({field: snapshot.get(field) for field in ('name', 'url', 'source', 'matched_by', 'matched_code', 'size_label', 'brand', 'code_warning')} |
                    {'site_selection': selection, 'image_token': image_token, 'reference_only': other_sources})
        return {'items': items[:8], 'auto_match': False,
                'state': 'found' if items else 'unavailable' if failures else 'not_found',
                'partial': incomplete, 'source': provider.PROVIDERS[key]['source'] if key else shop_name}

    def image(self, *, user_id, token):
        try:
            chosen = jwt.decode(token, signing_key(), algorithms=['HS256'])
            if chosen.get('user_id') != user_id or chosen.get('purpose') != 'receipt-thumbnail':
                raise ValueError('Invalid thumbnail token')
            return {'image': preview.thumbnail(chosen['url'], int(time.time() // 3600))}
        except (JWTError, ValueError, KeyError, OSError, httpx.HTTPError):
            return {'image': None}

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
