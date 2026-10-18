from datetime import datetime, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo
from sqlalchemy import select, update, or_
from app.db.models.catalog_product import CatalogProduct
from app.db.models.operation_item_template import OperationItemTemplate
from app.db.models.catalog_watch import CatalogWatch, CatalogOfferWatch, CatalogPriceEvent
from app.db.models.auth_identity import AuthIdentity
from app.db.models.item_source import ItemSource
from app.db.models.user import User
from app.services import retailer_price_provider as provider
from app.db.models.catalog_identity import CatalogOfferIdentity
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

    def provider(self, offer):
        source = self.db.get(ItemSource, offer.source_id) if offer.source_id else None
        return provider.source_provider(source.name if source else offer.shop_name)

    def supports(self, offer):
        return self.provider(offer) is not None

    def validate_source(self, offer, url):
        key, _ = provider.identify_url(url)
        if self.provider(offer) != key:
            raise ValueError('Сайт товара не соответствует источнику. Выберите источник этой сети.')

    def connect(self, user_id, product_id, template_id, url, expected_key, expected_name):
        offer = self.offer(user_id, product_id, template_id)
        self.validate_source(offer, url)
        snapshot = provider.fetch_product(url)
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
            self.observe(w, snapshot)
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
            from app.services.catalog_match_service import CatalogMatchService
            CatalogMatchService(self.db).pause(self.offer(user_id, product_id, template_id))
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
        supported = {}
        for t in self.db.scalars(select(OperationItemTemplate).where(OperationItemTemplate.user_id == user_id, OperationItemTemplate.product_id == product_id, OperationItemTemplate.is_archived.is_(False))):
            key = self.provider(t)
            if not key:
                continue
            identity = self.db.get(CatalogOfferIdentity, t.id)
            url = None
            if identity and identity.user_id == user_id and identity.product_url:
                try:
                    self.validate_source(t, identity.product_url)
                    _, url = provider.identify_url(identity.product_url)
                except ValueError:
                    pass
            from app.services.catalog_match_service import CatalogMatchService
            supported[t.id] = dict(provider.PROVIDERS[key], provider=key, saved_url=url, matching=CatalogMatchService(self.db).status(t))
        return {'supported_offer_ids': list(supported), 'supported_offers': supported, 'enabled': bool(w and w.enabled), 'telegram_connected': bool(self.db.scalar(select(AuthIdentity.id).where(AuthIdentity.user_id == user_id, AuthIdentity.provider == 'telegram').limit(1))),
                'offers': [self.serialize(o) for o in self.db.scalars(self.valid_offers().where(CatalogOfferWatch.user_id == user_id, CatalogOfferWatch.product_id == product_id))]}

    def dashboard(self, user_id, before_id=None):
        watches = list(self.db.scalars(select(CatalogWatch).join(CatalogProduct, CatalogProduct.id == CatalogWatch.product_id).where(CatalogWatch.user_id == user_id, CatalogWatch.enabled.is_(True), CatalogProduct.is_archived.is_(False))))
        ids = [w.product_id for w in watches]
        names = dict(self.db.execute(select(CatalogProduct.id, CatalogProduct.name).where(CatalogProduct.id.in_(ids))).all())
        offers = [dict(self.serialize(o), product_name=names[o.product_id]) for o in self.db.scalars(self.valid_offers().where(CatalogOfferWatch.user_id == user_id, CatalogOfferWatch.product_id.in_(ids)).order_by(CatalogOfferWatch.checked_at.desc()).limit(60))]
        connected_ids = set(self.db.scalars(self.valid_offers().with_only_columns(CatalogOfferWatch.product_id).where(CatalogOfferWatch.user_id == user_id, CatalogOfferWatch.product_id.in_(ids))))
        # Dashboard history survives Telegram delivery, unsubscribe and later resubscribe.
        stmt = select(CatalogPriceEvent).where(CatalogPriceEvent.user_id == user_id, self.notification_events())
        if before_id is not None:
            stmt = stmt.where(CatalogPriceEvent.id < before_id)
        page = list(self.db.scalars(stmt.order_by(CatalogPriceEvent.id.desc()).limit(21)))
        events = page[:20]
        from app.services.catalog_match_service import CatalogMatchService
        unresolved = []
        for product_id in ids:
            states, sources = [], {}
            for offer in self.db.scalars(select(OperationItemTemplate).where(OperationItemTemplate.user_id == user_id, OperationItemTemplate.product_id == product_id, OperationItemTemplate.is_archived.is_(False))):
                if self.supports(offer) and not self.db.get(CatalogOfferWatch, offer.id):
                    status = CatalogMatchService(self.db).status(offer)['state']
                    states.append(status)
                    sources.setdefault(status, []).append(provider.PROVIDERS[self.provider(offer)]['source'])
            if states or product_id not in connected_ids:
                state = next((s for s in ('choice', 'pending', 'error', 'not_found', 'missing_codes', 'paused') if s in states), 'missing_codes')
                unresolved.append({'product_id': product_id, 'name': names[product_id], 'matching_state': state, 'matching_sources': sorted(set(sources.get(state, [])))})
        all_offers = list(self.db.scalars(self.valid_offers().where(CatalogOfferWatch.user_id == user_id)))
        monitoring = {'connected': len(all_offers),
                      'checked': sum(bool(o.checked_at and not o.error) for o in all_offers),
                      'errors': sum(bool(o.error) for o in all_offers)}
        return {'monitoring': monitoring, 'tracked_count': len(ids), 'offers': offers, 'events': [dict(e.data, id=e.id, product_id=e.product_id, created_at=e.created_at) for e in events], 'unlinked': unresolved, 'next_cursor': events[-1].id if len(page) > 20 else None}

    @staticmethod
    def notification_events():
        # Missing flag identifies notifications created before independent site history.
        flag = CatalogPriceEvent.data['notification'].as_boolean()
        return or_(flag.is_(None), flag.is_(True))

    def observe(self, w, snapshot, *, stamp=None, notification=False, extra=None):
        self.db.add(CatalogPriceEvent(user_id=w.user_id, product_id=w.product_id,
            template_id=w.template_id, created_at=stamp or now(),
            telegram_sent_at=None if notification else now(),
            data={**snapshot, **(extra or {}), 'notification': notification}))

    def history(self, user_id, product_id, template_id, before_id=None):
        self.offer(user_id, product_id, template_id)
        stmt = select(CatalogPriceEvent).where(CatalogPriceEvent.user_id == user_id,
            CatalogPriceEvent.template_id == template_id)
        if before_id:
            stmt = stmt.where(CatalogPriceEvent.id < before_id)
        page = list(self.db.scalars(stmt.order_by(CatalogPriceEvent.id.desc()).limit(201)))
        rows = [dict(e.data, id=e.id, recorded_at=e.created_at) for e in page[:200]]
        # Existing links have a real last observation even before history was enabled.
        w = self.db.get(CatalogOfferWatch, template_id)
        if not before_id and w and w.user_id == user_id and w.snapshot:
            rows.insert(0, dict(w.snapshot, id=None, recorded_at=w.checked_at))
        return {'items': rows, 'next_cursor': page[199].id if len(page) > 200 else None}

    def record(self, w, snapshot):
        previous = w.snapshot or {}
        # Availability, package changes, and conditional terms cannot create a price-drop claim.
        comparable = previous.get('comparison_key') == snapshot['comparison_key'] and previous.get('conditions_key') == snapshot.get('conditions_key')
        changed = comparable and previous.get('available') and snapshot['available'] and Decimal(previous['price']) != Decimal(snapshot['price'])
        enabled = self.db.get(CatalogWatch, w.product_id)
        latest = self.db.scalar(select(CatalogPriceEvent.id).where(
            CatalogPriceEvent.user_id == w.user_id, CatalogPriceEvent.template_id == w.template_id).limit(1))
        if not latest and previous:
            self.observe(w, previous, stamp=w.checked_at)
        keys = ('price', 'regular_price', 'available', 'comparison_key', 'conditions_key', 'url')
        if not previous or any(previous.get(k) != snapshot.get(k) for k in keys):
            notify = bool(changed and enabled and enabled.enabled)
            extra = {}
            if changed:
                old, new = Decimal(previous['price']), Decimal(snapshot['price'])
                extra = {'product_name': self.product(w.user_id, w.product_id).name,
                         'old_price': str(old),
                         'percent': str(((new-old)/old*100).quantize(Decimal('.1'))) if old else None,
                         'direction': 'down' if new < old else 'up'}
            self.observe(w, snapshot, notification=notify, extra=extra)
        w.snapshot = snapshot
        w.checked_at = now()
        w.next_check_at = now() + timedelta(hours=6)
        w.error = None if comparable or not previous else 'Карточка или условия изменились: сравнение начато заново.'
        self.db.commit()

    def refresh_due(self, limit=3):
        rows = list(self.db.scalars(self.valid_offers().where(CatalogOfferWatch.next_check_at <= now()).order_by(CatalogOfferWatch.next_check_at).limit(limit)))
        for w in rows:
            with try_background_job_lock(self.db, f'catalog_offer_watch:{w.template_id}') as acquired:
                if not acquired:
                    continue
                self.db.refresh(w)
                due = w.next_check_at.replace(tzinfo=timezone.utc) if w.next_check_at.tzinfo is None else w.next_check_at
                if due > now():
                    continue
                try:
                    offer = self.offer(w.user_id, w.product_id, w.template_id)
                    self.validate_source(offer, w.url)
                    self.record(w, provider.fetch_product(w.url))
                except (ValueError, LookupError) as exc:
                    w.error = str(exc)[:300]
                    w.next_check_at = now() + timedelta(hours=1)
                    self.db.commit()

    def deliveries(self):
        stmt = select(CatalogPriceEvent).join(CatalogWatch, CatalogWatch.product_id == CatalogPriceEvent.product_id).join(CatalogProduct, CatalogProduct.id == CatalogPriceEvent.product_id).join(OperationItemTemplate, OperationItemTemplate.id == CatalogPriceEvent.template_id).join(CatalogOfferWatch, CatalogOfferWatch.template_id == CatalogPriceEvent.template_id).where(CatalogWatch.enabled.is_(True), CatalogProduct.is_archived.is_(False), OperationItemTemplate.is_archived.is_(False), OperationItemTemplate.product_id == CatalogPriceEvent.product_id, CatalogPriceEvent.telegram_sent_at.is_(None), CatalogPriceEvent.created_at >= CatalogWatch.enabled_at).order_by(CatalogPriceEvent.id)
        eligible = select(AuthIdentity.user_id).join(User, User.id == AuthIdentity.user_id).where(AuthIdentity.provider == 'telegram', User.status.in_(['approved', 'active']))
        stmt = stmt.where(CatalogPriceEvent.user_id.in_(eligible), self.notification_events())
        grouped = {}
        for e in self.db.scalars(stmt):
            grouped.setdefault(e.user_id, []).append(e)
        for user_id, events in grouped.items():
            stamps = [e.created_at.replace(tzinfo=timezone.utc) if e.created_at.tzinfo is None else e.created_at for e in events]
            # Gather a refresh wave, but cap the wait when changes keep arriving.
            if now() - max(stamps) < timedelta(minutes=15) and now() - min(stamps) < timedelta(hours=1):
                continue
            chat = self.db.scalar(select(AuthIdentity.provider_user_id).join(User, User.id == AuthIdentity.user_id).where(AuthIdentity.user_id == user_id, AuthIdentity.provider == 'telegram', User.status.in_(['approved', 'active'])).limit(1))
            if not chat:
                continue
            # Retailers use long slug URLs; count text as well as event count.
            batch = []
            for event in events:
                candidate = batch + [event]
                if batch and (len(candidate) > 4 or len(self.message(candidate).encode('utf-16-le')) // 2 > 3800):
                    yield chat, batch, self.message(batch)
                    batch = []
                batch.append(event)
            if batch:
                yield chat, batch, self.message(batch)

    @staticmethod
    def message(events):
        lines = ['Дайджест цен на товары', '']
        for event in events:
            d = event.data
            stamp = event.created_at
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            lines.extend([f"{'🟢 Снижение' if d['direction']=='down' else '🔺 Повышение'} · {d['percent']}%", d['product_name'][:100], d.get('source', 'Е-доставка')])
            if d['name'] != d['product_name']:
                lines.append(d['name'][:100])
            lines.extend([f"{d['old_price']} → {d['price']} BYN / {d['unit']}", d['normalized'], d['conditions'], 'Проверено: ' + stamp.astimezone(ZoneInfo('Europe/Minsk')).strftime('%d.%m.%Y %H:%M'), d['url'], ''])
        lines.append('Цены сайта. Наличие и итоговую цену проверьте перед заказом.')
        return '\n'.join(lines)
