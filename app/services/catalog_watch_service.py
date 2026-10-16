from datetime import datetime, timedelta, timezone
from decimal import Decimal
import re
from zoneinfo import ZoneInfo
from sqlalchemy import select, update
from app.db.models.catalog_product import CatalogProduct
from app.db.models.operation_item_template import OperationItemTemplate
from app.db.models.catalog_watch import CatalogWatch, CatalogOfferWatch, CatalogPriceEvent
from app.db.models.auth_identity import AuthIdentity
from app.db.models.item_source import ItemSource
from app.db.models.user import User
from app.services import edostavka_provider
from app.services.background_job_lock import try_background_job_lock


def now():
    return datetime.now(timezone.utc)


class CatalogWatchService:
    def __init__(self, db):
        self.db = db

    def product(self, user_id, product_id):
        p = self.db.get(CatalogProduct, product_id)
        if not p or p.user_id != user_id or p.is_archived:
            raise LookupError('Товар не найден')
        return p

    def offer(self, user_id, product_id, template_id):
        self.product(user_id, product_id)
        t = self.db.get(OperationItemTemplate, template_id)
        if not t or t.user_id != user_id or t.product_id != product_id or t.is_archived:
            raise LookupError('Предложение не найдено')
        return t

    def set_enabled(self, user_id, product_id, enabled):
        self.product(user_id, product_id)
        w = self.db.get(CatalogWatch, product_id)
        if not w:
            w = CatalogWatch(product_id=product_id, user_id=user_id, enabled=False)
            self.db.add(w)
        if bool(w.enabled) != enabled:
            w.enabled_at = now()
            # Pending notifications from a previous subscription must not be replayed.
            self.db.execute(update(CatalogPriceEvent).where(CatalogPriceEvent.user_id == user_id, CatalogPriceEvent.product_id == product_id, CatalogPriceEvent.telegram_sent_at.is_(None)).values(telegram_sent_at=now()))
        w.enabled = enabled
        self.db.commit()
        return self.detail(user_id, product_id)

    def supports(self, offer):
        source = self.db.get(ItemSource, offer.source_id) if offer.source_id else None
        name = (source.name if source else offer.shop_name) or ''
        normalized = re.sub(r'[^a-zа-яё]', '', name.lower())
        return normalized in {'едоставка', 'евроопт', 'edostavka', 'edostavkaby', 'euroopt'}

    def connect(self, user_id, product_id, template_id, url, expected_key, expected_name):
        offer = self.offer(user_id, product_id, template_id)
        if not self.supports(offer):
            raise ValueError('Добавьте источник «Е-доставка» для цены этого сайта. Другие сети пока не подключены.')
        snapshot = edostavka_provider.fetch_product(url)
        if snapshot['comparison_key'] != expected_key or snapshot['name'] != expected_name:
            raise ValueError('Карточка изменилась. Проверьте товар ещё раз перед подключением.')
        with try_background_job_lock(self.db, f'catalog_offer_watch:{template_id}') as acquired:
            if not acquired:
                raise ValueError('Идёт проверка предложения. Повторите через несколько секунд.')
            w = self.db.get(CatalogOfferWatch, template_id)
            if not w:
                w = CatalogOfferWatch(template_id=template_id, product_id=product_id, user_id=user_id)
                self.db.add(w)
            w.product_id = product_id
            w.url = snapshot['url']
            w.snapshot = snapshot
            w.checked_at = now()
            w.next_check_at = now() + timedelta(hours=6)
            w.error = None
            self.db.execute(update(CatalogPriceEvent).where(CatalogPriceEvent.user_id == user_id, CatalogPriceEvent.template_id == template_id, CatalogPriceEvent.telegram_sent_at.is_(None)).values(telegram_sent_at=now()))
            self.db.commit()
        return self.detail(user_id, product_id)

    def disconnect(self, user_id, product_id, template_id):
        self.offer(user_id, product_id, template_id)
        with try_background_job_lock(self.db, f'catalog_offer_watch:{template_id}') as acquired:
            if not acquired:
                raise ValueError('Идёт проверка предложения. Повторите через несколько секунд.')
            w = self.db.get(CatalogOfferWatch, template_id)
            if w:
                self.db.delete(w)
            self.db.execute(update(CatalogPriceEvent).where(CatalogPriceEvent.user_id == user_id, CatalogPriceEvent.template_id == template_id, CatalogPriceEvent.telegram_sent_at.is_(None)).values(telegram_sent_at=now()))
            self.db.commit()
        return self.detail(user_id, product_id)

    def valid_offers(self):
        return select(CatalogOfferWatch).join(OperationItemTemplate, OperationItemTemplate.id == CatalogOfferWatch.template_id).join(CatalogProduct, CatalogProduct.id == CatalogOfferWatch.product_id).where(OperationItemTemplate.product_id == CatalogOfferWatch.product_id, OperationItemTemplate.is_archived.is_(False), CatalogProduct.is_archived.is_(False))

    @staticmethod
    def serialize(w):
        return {'template_id': w.template_id, 'product_id': w.product_id, 'snapshot': w.snapshot, 'checked_at': w.checked_at, 'error': w.error}

    def detail(self, user_id, product_id):
        self.product(user_id, product_id)
        w = self.db.get(CatalogWatch, product_id)
        return {'supported_offer_ids': [t.id for t in self.db.scalars(select(OperationItemTemplate).where(OperationItemTemplate.user_id == user_id, OperationItemTemplate.product_id == product_id, OperationItemTemplate.is_archived.is_(False))) if self.supports(t)], 'enabled': bool(w and w.enabled), 'telegram_connected': bool(self.db.scalar(select(AuthIdentity.id).where(AuthIdentity.user_id == user_id, AuthIdentity.provider == 'telegram').limit(1))),
                'offers': [self.serialize(o) for o in self.db.scalars(self.valid_offers().where(CatalogOfferWatch.user_id == user_id, CatalogOfferWatch.product_id == product_id))]}

    def dashboard(self, user_id):
        watches = list(self.db.scalars(select(CatalogWatch).join(CatalogProduct, CatalogProduct.id == CatalogWatch.product_id).where(CatalogWatch.user_id == user_id, CatalogWatch.enabled.is_(True), CatalogProduct.is_archived.is_(False))))
        ids = [w.product_id for w in watches]
        names = dict(self.db.execute(select(CatalogProduct.id, CatalogProduct.name).where(CatalogProduct.id.in_(ids))).all())
        offers = [dict(self.serialize(o), product_name=names[o.product_id]) for o in self.db.scalars(self.valid_offers().where(CatalogOfferWatch.user_id == user_id, CatalogOfferWatch.product_id.in_(ids)).order_by(CatalogOfferWatch.checked_at.desc()).limit(60))]
        connected_ids = set(self.db.scalars(self.valid_offers().with_only_columns(CatalogOfferWatch.product_id).where(CatalogOfferWatch.user_id == user_id, CatalogOfferWatch.product_id.in_(ids))))
        events = self.db.scalars(select(CatalogPriceEvent).join(CatalogWatch, CatalogWatch.product_id == CatalogPriceEvent.product_id).where(CatalogPriceEvent.user_id == user_id, CatalogPriceEvent.product_id.in_(ids), CatalogPriceEvent.created_at >= CatalogWatch.enabled_at).order_by(CatalogPriceEvent.id.desc()).limit(20))
        return {'tracked_count': len(ids), 'offers': offers, 'events': [dict(e.data, id=e.id, product_id=e.product_id, created_at=e.created_at) for e in events], 'unlinked': [{'product_id': i, 'name': names[i]} for i in ids if i not in connected_ids]}

    def record(self, w, snapshot):
        previous = w.snapshot or {}
        # Availability, package changes, and conditional terms cannot create a price-drop claim.
        comparable = previous.get('comparison_key') == snapshot['comparison_key'] and previous.get('conditions_key') == snapshot.get('conditions_key')
        changed = comparable and previous.get('available') and snapshot['available'] and Decimal(previous['price']) != Decimal(snapshot['price'])
        enabled = self.db.get(CatalogWatch, w.product_id)
        if changed and enabled and enabled.enabled:
            old, new = Decimal(previous['price']), Decimal(snapshot['price'])
            p = self.product(w.user_id, w.product_id)
            self.db.add(CatalogPriceEvent(user_id=w.user_id, product_id=w.product_id, template_id=w.template_id, created_at=now(), data={**snapshot, 'product_name': p.name, 'old_price': str(old), 'percent': str(((new-old)/old*100).quantize(Decimal('.1'))), 'direction': 'down' if new < old else 'up'}))
        w.snapshot = snapshot
        w.checked_at = now()
        w.next_check_at = now() + timedelta(hours=6)
        w.error = None if comparable or not previous else 'Карточка или условия изменились: сравнение начато заново.'
        self.db.commit()

    def refresh_due(self, limit=3):
        rows = list(self.db.scalars(self.valid_offers().join(CatalogWatch, CatalogWatch.product_id == CatalogOfferWatch.product_id).where(CatalogWatch.enabled.is_(True), CatalogOfferWatch.next_check_at <= now()).order_by(CatalogOfferWatch.next_check_at).limit(limit)))
        for w in rows:
            with try_background_job_lock(self.db, f'catalog_offer_watch:{w.template_id}') as acquired:
                if not acquired:
                    continue
                self.db.refresh(w)
                due = w.next_check_at.replace(tzinfo=timezone.utc) if w.next_check_at.tzinfo is None else w.next_check_at
                if due > now():
                    continue
                try:
                    self.record(w, edostavka_provider.fetch_product(w.url))
                except (edostavka_provider.RetailerUnavailable, ValueError) as exc:
                    w.error = str(exc)[:300]
                    w.next_check_at = now() + timedelta(hours=1)
                    self.db.commit()

    def deliveries(self):
        stmt = select(CatalogPriceEvent).join(CatalogWatch, CatalogWatch.product_id == CatalogPriceEvent.product_id).join(CatalogProduct, CatalogProduct.id == CatalogPriceEvent.product_id).join(OperationItemTemplate, OperationItemTemplate.id == CatalogPriceEvent.template_id).join(CatalogOfferWatch, CatalogOfferWatch.template_id == CatalogPriceEvent.template_id).where(CatalogWatch.enabled.is_(True), CatalogProduct.is_archived.is_(False), OperationItemTemplate.is_archived.is_(False), OperationItemTemplate.product_id == CatalogPriceEvent.product_id, CatalogPriceEvent.telegram_sent_at.is_(None), CatalogPriceEvent.created_at >= CatalogWatch.enabled_at, CatalogPriceEvent.created_at >= now()-timedelta(days=2)).order_by(CatalogPriceEvent.id)
        eligible = select(AuthIdentity.user_id).join(User, User.id == AuthIdentity.user_id).where(AuthIdentity.provider == 'telegram', User.status.in_(['approved', 'active']))
        stmt = stmt.where(CatalogPriceEvent.user_id.in_(eligible))
        grouped = {}
        for e in self.db.scalars(stmt.limit(200)):
            grouped.setdefault(e.user_id, []).append(e)
        for user_id, events in grouped.items():
            chat = self.db.scalar(select(AuthIdentity.provider_user_id).join(User, User.id == AuthIdentity.user_id).where(AuthIdentity.user_id == user_id, AuthIdentity.provider == 'telegram', User.status.in_(['approved', 'active'])).limit(1))
            if not chat:
                continue
            # Bounded batches fit Telegram's 4096-character message limit.
            for start in range(0, len(events), 4):
                batch = events[start:start+4]
                yield chat, batch, self.message(batch)

    @staticmethod
    def message(events):
        lines = ['Изменения цен · Е-доставка', '']
        for event in events:
            d = event.data
            stamp = event.created_at
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            lines.extend([f"{'🟢 Снижение' if d['direction']=='down' else '🔺 Повышение'} · {d['percent']}%", d['product_name'][:100]])
            if d['name'] != d['product_name']:
                lines.append(d['name'][:100])
            lines.extend([f"{d['old_price']} → {d['price']} BYN / {d['unit']}", d['normalized'], d['conditions'], 'Проверено: ' + stamp.astimezone(ZoneInfo('Europe/Minsk')).strftime('%d.%m.%Y %H:%M'), d['url'], ''])
        lines.append('Цены сайта. Наличие и итоговую цену проверьте перед заказом.')
        return '\n'.join(lines)
