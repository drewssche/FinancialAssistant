"""Match retailer cards by independently verified codes, never by search rank."""
import hashlib
import json
from datetime import timedelta, timezone
from sqlalchemy import select
from app.db.models.catalog_identity import CatalogOfferIdentity, CatalogVariant, CatalogVariantCode
from app.db.models.catalog_product import CatalogProduct
from app.db.models.operation_item_template import OperationItemTemplate
from app.db.models.catalog_watch import CatalogOfferMatch, CatalogOfferWatch, CatalogWatch
from app.services.catalog_identity_service import normalize_codes
from app.services.catalog_watch_service import CatalogWatchService, now
from app.services.background_job_lock import try_background_job_lock
from app.services import retailer_price_provider as provider


def barcodes(values):
    result = set()
    for value in values:
        try:
            result.update(normalize_codes([str(value)]))
        except ValueError:
            continue
    return result


class CatalogMatchService:
    def __init__(self, db):
        self.db = db
        self.watch = CatalogWatchService(db)

    def context(self, offer):
        product = self.watch.product(offer.user_id, offer.product_id)
        identity = self.db.get(CatalogOfferIdentity, offer.id)
        variants = list(self.db.scalars(select(CatalogVariant).where(
            CatalogVariant.product_id == product.id, CatalogVariant.user_id == offer.user_id,
            CatalogVariant.is_archived.is_(False))))
        if identity and identity.variant_id:
            variants = [v for v in variants if v.id == identity.variant_id]
        else:
            # Only the current package's codes; historical sizes must not leak in.
            variants = [v for v in variants if (v.sale_unit, v.package_quantity, v.package_unit) ==
                        (product.sale_unit, product.package_quantity, product.package_unit)]
        codes = list(self.db.scalars(select(CatalogVariantCode.code).where(
            CatalogVariantCode.user_id == offer.user_id,
            CatalogVariantCode.variant_id.in_([v.id for v in variants]))))
        context = {'product_id': product.id, 'source_id': offer.source_id,
                   'provider': self.watch.provider(offer), 'barcodes': sorted(barcodes(codes)),
                   'barcode_queries': sorted(set(c for c in codes if barcodes([c]))),
                   'article': (identity.retailer_code or '').strip() if identity else '',
                   'variant_ids': sorted(v.id for v in variants),
                   'size': [str(product.package_quantity), product.package_unit, product.sale_unit],
                   'saved_url': identity.product_url if identity else None}
        fingerprint = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()
        return context, fingerprint

    def status(self, offer):
        context, fingerprint = self.context(offer)
        row = self.db.get(CatalogOfferMatch, offer.id)
        if row and row.user_id == offer.user_id and row.state == 'paused':
            return {'state': 'paused', 'candidates': []}
        if not context['barcodes'] and not context['article']:
            return {'state': 'missing_codes', 'candidates': []}
        if not row or row.fingerprint != fingerprint:
            return {'state': 'pending', 'candidates': []}
        return {'state': row.state, 'candidates': row.candidates, 'error': row.error}

    def pause(self, offer):
        _, fingerprint = self.context(offer)
        row = self.db.get(CatalogOfferMatch, offer.id)
        if row is None:
            row = CatalogOfferMatch(template_id=offer.id, user_id=offer.user_id)
            self.db.add(row)
        row.fingerprint, row.state, row.candidates = fingerprint, 'paused', []
        row.error, row.next_check_at = None, now()

    def queue(self, user_id, product_id, template_id):
        self.watch.offer(user_id, product_id, template_id)
        for offer in self.db.scalars(select(OperationItemTemplate).where(
            OperationItemTemplate.user_id == user_id, OperationItemTemplate.product_id == product_id,
            OperationItemTemplate.id == template_id, OperationItemTemplate.is_archived.is_(False))):
            if not self.watch.supports(offer) or self.db.get(CatalogOfferWatch, offer.id):
                continue
            with try_background_job_lock(self.db, f'catalog_offer_watch:{offer.id}') as acquired:
                if not acquired:
                    continue
                _, fingerprint = self.context(offer)
                row = self.db.get(CatalogOfferMatch, offer.id)
                if row is None:
                    row = CatalogOfferMatch(template_id=offer.id, user_id=user_id)
                    self.db.add(row)
                row.fingerprint, row.state, row.candidates = fingerprint, 'pending', []
                row.error, row.next_check_at = None, now()
                self.db.commit()

    def discover(self, offer):
        with try_background_job_lock(self.db, f'catalog_offer_watch:{offer.id}') as acquired:
            if not acquired:
                return False
            self.db.expire_all()
            if self.db.get(CatalogOfferWatch, offer.id):
                return False
            offer = self.watch.offer(offer.user_id, offer.product_id, offer.id)
            context, fingerprint = self.context(offer)
            row = self.db.get(CatalogOfferMatch, offer.id)
            if row and row.state == 'paused':
                return False
            if row and row.fingerprint == fingerprint:
                due = row.next_check_at.replace(tzinfo=timezone.utc) if row.next_check_at.tzinfo is None else row.next_check_at
                if due > now():
                    return False
            if not context['provider']:
                return False
            if row is None:
                row = CatalogOfferMatch(template_id=offer.id, user_id=offer.user_id)
                self.db.add(row)
            row.fingerprint, row.candidates, row.error = fingerprint, [], None
            row.next_check_at = now() + timedelta(hours=6)
            queries = [(code, 'barcode') for code in context['barcode_queries']]
            if context['article']:
                queries.append((context['article'], 'retailer'))
            if not queries:
                row.state = 'missing_codes'
                self.db.commit()
                return False
            candidates = []
            state, error, delay = 'not_found', None, 6
            try:
                hits, exact, incomplete = {}, {}, False
                # Many codes require a choice, not an arbitrarily truncated auto-link.
                incomplete = len(queries) > 8
                for query, kind in queries[:8]:
                    found = provider.search_products(context['provider'], query, kind)
                    incomplete |= len(found) >= (3 if context['provider'] == 'sosedi' else 8)
                    for hit in found:
                        key, url = provider.identify_url(hit['url'])
                        if key != context['provider']:
                            raise ValueError('Сайт результата не соответствует источнику')
                        hits[url] = hit
                # A stored URL is only a candidate, not proof of a code match.
                if context['saved_url']:
                    self.watch.validate_source(offer, context['saved_url'])
                    hits.setdefault(provider.identify_url(context['saved_url'])[1], {})
                incomplete |= len(hits) > 16
                for url, hit in list(hits.items())[:16]:
                    snapshot = provider.fetch_product(url)
                    ids = snapshot.get('identifiers', {})
                    actual_barcodes = barcodes(ids.get('barcodes', []))
                    barcode_match = bool(actual_barcodes.intersection(context['barcodes']))
                    article_match = bool(context['article'] and ids.get('article') == context['article'])
                    conflict = bool(context['barcodes'] and actual_barcodes and not barcode_match)
                    proven = (barcode_match or article_match) and not conflict
                    incomplete |= conflict
                    candidates.append({
                        **{k: snapshot[k] for k in ('url', 'name', 'price', 'unit', 'available')},
                        'exact': proven, 'conflict': conflict})
                    if proven:
                        exact[url] = snapshot
                # Editing codes while a site request is in flight invalidates the result.
                self.db.expire(offer)
                self.db.expire_all()
                fresh_context, fresh_fingerprint = self.context(offer)
                if fresh_fingerprint != fingerprint or offer.is_archived:
                    self.db.rollback()
                    return False
                if len(exact) == 1 and not incomplete:
                    snapshot = next(iter(exact.values()))
                    self.db.add(CatalogOfferWatch(template_id=offer.id, user_id=offer.user_id,
                        product_id=offer.product_id, url=snapshot['url'], snapshot=snapshot,
                        checked_at=now(), next_check_at=now()+timedelta(hours=6)))
                    state = 'linked'
                else:
                    state = 'choice' if hits else 'not_found'
            except (ValueError, LookupError) as exc:
                state, error, delay = 'error', str(exc)[:300], 1
            row.fingerprint, row.candidates, row.error = fingerprint, candidates, error
            row.state, row.next_check_at = state, now() + timedelta(hours=delay)
            self.db.commit()
            return True

    def discover_pending(self, limit=2, user_id=None):
        stmt = select(OperationItemTemplate).join(CatalogProduct, CatalogProduct.id == OperationItemTemplate.product_id).outerjoin(
            CatalogOfferWatch, CatalogOfferWatch.template_id == OperationItemTemplate.id).outerjoin(
            CatalogOfferMatch, CatalogOfferMatch.template_id == OperationItemTemplate.id).outerjoin(
            CatalogWatch, CatalogWatch.product_id == CatalogProduct.id).where(
            OperationItemTemplate.is_archived.is_(False), CatalogProduct.is_archived.is_(False),
            CatalogOfferWatch.template_id.is_(None)).order_by(
            CatalogWatch.enabled.desc().nullslast(), CatalogOfferMatch.next_check_at.asc().nullslast(), OperationItemTemplate.id)
        if user_id is not None:
            stmt = stmt.where(OperationItemTemplate.user_id == user_id)
        processed = 0
        for offer in self.db.scalars(stmt).all():
            if self.discover(offer):
                processed += 1
            if processed >= limit:
                break
        return processed
