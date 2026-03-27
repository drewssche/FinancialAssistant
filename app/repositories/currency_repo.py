from datetime import date

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from app.db.models import AuthIdentity, FxRateSnapshot, FxTrade, UserPreference


class CurrencyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_trade(self, trade: FxTrade) -> FxTrade:
        self.db.add(trade)
        self.db.flush()
        return trade

    def list_trades(self, *, user_id: int, asset_currency: str | None = None, limit: int = 200) -> list[FxTrade]:
        stmt = select(FxTrade).where(FxTrade.user_id == user_id)
        if asset_currency:
            stmt = stmt.where(FxTrade.asset_currency == asset_currency)
        stmt = stmt.order_by(FxTrade.trade_date.desc(), FxTrade.id.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def list_all_trades(self, *, user_id: int) -> list[FxTrade]:
        stmt = (
            select(FxTrade)
            .where(FxTrade.user_id == user_id)
            .order_by(FxTrade.asset_currency.asc(), FxTrade.trade_date.asc(), FxTrade.id.asc())
        )
        return list(self.db.scalars(stmt))

    def get_latest_rate_map(self, *, user_id: int) -> dict[str, FxRateSnapshot]:
        rows = self.db.execute(
            select(FxRateSnapshot)
            .where(FxRateSnapshot.user_id == user_id)
            .order_by(FxRateSnapshot.currency.asc(), FxRateSnapshot.rate_date.desc(), FxRateSnapshot.id.desc())
        ).scalars()
        latest: dict[str, FxRateSnapshot] = {}
        for row in rows:
            latest.setdefault(row.currency, row)
        return latest

    def get_latest_rate_pair_map(self, *, user_id: int) -> dict[str, tuple[FxRateSnapshot, FxRateSnapshot | None]]:
        rows = self.db.execute(
            select(FxRateSnapshot)
            .where(FxRateSnapshot.user_id == user_id)
            .order_by(FxRateSnapshot.currency.asc(), FxRateSnapshot.rate_date.desc(), FxRateSnapshot.id.desc())
        ).scalars()
        pairs: dict[str, list[FxRateSnapshot]] = {}
        for row in rows:
            items = pairs.setdefault(row.currency, [])
            if len(items) < 2:
                items.append(row)
        return {
            currency: (items[0], items[1] if len(items) > 1 else None)
            for currency, items in pairs.items()
            if items
        }

    def upsert_rate(
        self,
        *,
        user_id: int,
        currency: str,
        rate_date: date,
        rate,
        source: str,
    ) -> FxRateSnapshot:
        row = self.db.scalar(
            select(FxRateSnapshot).where(
                FxRateSnapshot.user_id == user_id,
                FxRateSnapshot.currency == currency,
                FxRateSnapshot.rate_date == rate_date,
            )
        )
        if row:
            row.rate = rate
            row.source = source
            self.db.flush()
            return row
        row = FxRateSnapshot(
            user_id=user_id,
            currency=currency,
            rate_date=rate_date,
            rate=rate,
            source=source,
        )
        self.db.add(row)
        self.db.flush()
        return row

    def list_rate_history(
        self,
        *,
        user_id: int,
        currency: str,
        limit: int = 120,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[FxRateSnapshot]:
        stmt = select(FxRateSnapshot).where(
            FxRateSnapshot.user_id == user_id,
            FxRateSnapshot.currency == currency,
        )
        if date_from:
            stmt = stmt.where(FxRateSnapshot.rate_date >= date_from)
        if date_to:
            stmt = stmt.where(FxRateSnapshot.rate_date <= date_to)
        stmt = stmt.order_by(desc(FxRateSnapshot.rate_date), desc(FxRateSnapshot.id)).limit(limit)
        return list(reversed(list(self.db.scalars(stmt))))

    def list_currency_preferences(self) -> list[UserPreference]:
        stmt = select(UserPreference).order_by(UserPreference.user_id.asc())
        return list(self.db.scalars(stmt))

    def list_telegram_digest_targets(self) -> list:
        stmt = (
            select(AuthIdentity, UserPreference)
            .outerjoin(UserPreference, UserPreference.user_id == AuthIdentity.user_id)
            .where(AuthIdentity.provider == "telegram")
            .order_by(AuthIdentity.user_id.asc())
        )
        return list(self.db.execute(stmt).all())
