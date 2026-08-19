from datetime import date, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuthIdentity,
    FxBankRate,
    FxRateSnapshot,
    FxTrade,
    PlanOperation,
    User,
    UserPreference,
)

NBRB_RATE_SOURCES = ("nbrb_auto_unit", "nbrb_history_unit")


class CurrencyRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_trade(self, trade: FxTrade) -> FxTrade:
        self.db.add(trade)
        self.db.flush()
        return trade

    def get_trade(self, *, user_id: int, trade_id: int) -> FxTrade | None:
        stmt = select(FxTrade).where(
            FxTrade.user_id == user_id,
            FxTrade.id == trade_id,
        )
        return self.db.scalar(stmt)

    def get_trade_by_linked_operation_id(self, *, user_id: int, operation_id: int) -> FxTrade | None:
        stmt = select(FxTrade).where(
            FxTrade.user_id == user_id,
            FxTrade.linked_operation_id == operation_id,
        )
        return self.db.scalar(stmt)

    def list_trades(self, *, user_id: int, asset_currency: str | None = None, limit: int = 200) -> list[FxTrade]:
        stmt = select(FxTrade).where(FxTrade.user_id == user_id)
        if asset_currency:
            stmt = stmt.where(FxTrade.asset_currency == asset_currency)
        stmt = stmt.order_by(FxTrade.trade_date.desc(), FxTrade.id.desc()).limit(limit)
        return list(self.db.scalars(stmt))

    def list_trades_paginated(
        self,
        *,
        user_id: int,
        asset_currency: str | None = None,
        page: int,
        page_size: int,
    ) -> tuple[list[FxTrade], int]:
        stmt = select(FxTrade).where(FxTrade.user_id == user_id)
        count_stmt = select(func.count()).select_from(FxTrade).where(FxTrade.user_id == user_id)
        if asset_currency:
            stmt = stmt.where(FxTrade.asset_currency == asset_currency)
            count_stmt = count_stmt.where(FxTrade.asset_currency == asset_currency)
        total = int(self.db.scalar(count_stmt) or 0)
        items = list(
            self.db.scalars(
                stmt
                .order_by(FxTrade.trade_date.desc(), FxTrade.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return items, total

    def list_all_trades(self, *, user_id: int) -> list[FxTrade]:
        stmt = (
            select(FxTrade)
            .where(FxTrade.user_id == user_id)
            .order_by(FxTrade.asset_currency.asc(), FxTrade.trade_date.asc(), FxTrade.id.asc())
        )
        return list(self.db.scalars(stmt))

    def lock_user_currency_ledger(self, *, user_id: int) -> None:
        # The user row is guaranteed to exist even when their ledger is empty,
        # which makes it a stable lock target for concurrent balance changes.
        self.db.scalar(select(User.id).where(User.id == user_id).with_for_update())

    def list_trades_for_period(
        self,
        *,
        user_id: int,
        date_from: date,
        date_to: date,
    ) -> list[FxTrade]:
        stmt = (
            select(FxTrade)
            .where(
                FxTrade.user_id == user_id,
                FxTrade.trade_date >= date_from,
                FxTrade.trade_date <= date_to,
            )
            .order_by(FxTrade.trade_date.asc(), FxTrade.id.asc())
        )
        return list(self.db.scalars(stmt))

    def delete_trade(self, trade: FxTrade) -> None:
        self.db.delete(trade)
        self.db.flush()

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

    def get_latest_nbrb_rate_map(self, *, user_id: int) -> dict[str, FxRateSnapshot]:
        rows = self.db.execute(
            select(FxRateSnapshot)
            .where(
                FxRateSnapshot.user_id == user_id,
                FxRateSnapshot.source.in_(NBRB_RATE_SOURCES),
            )
            .order_by(FxRateSnapshot.currency.asc(), FxRateSnapshot.rate_date.desc(), FxRateSnapshot.id.desc())
        ).scalars()
        latest: dict[str, FxRateSnapshot] = {}
        for row in rows:
            latest.setdefault(row.currency, row)
        return latest

    def get_nbrb_rate_as_of(
        self,
        *,
        user_id: int,
        currency: str,
        rate_date: date,
    ) -> FxRateSnapshot | None:
        """Return the latest known NBRB rate on or before ``rate_date``.

        The preceding-day lookup is intentional: NBRB does not publish a new
        snapshot for every weekend/holiday, while an operation still needs the
        rate that was effective on that date.
        """
        stmt = (
            select(FxRateSnapshot)
            .where(
                FxRateSnapshot.user_id == user_id,
                FxRateSnapshot.currency == currency,
                FxRateSnapshot.rate_date <= rate_date,
                FxRateSnapshot.source.in_(NBRB_RATE_SOURCES),
            )
            .order_by(FxRateSnapshot.rate_date.desc(), FxRateSnapshot.id.desc())
            .limit(1)
        )
        return self.db.scalar(stmt)

    def get_latest_rate_triplet_map(
        self,
        *,
        user_id: int,
    ) -> dict[str, tuple[FxRateSnapshot, FxRateSnapshot | None, FxRateSnapshot | None]]:
        rows = self.db.execute(
            select(FxRateSnapshot)
            .where(FxRateSnapshot.user_id == user_id)
            .order_by(FxRateSnapshot.currency.asc(), FxRateSnapshot.rate_date.desc(), FxRateSnapshot.id.desc())
        ).scalars()
        pairs: dict[str, list[FxRateSnapshot]] = {}
        for row in rows:
            items = pairs.setdefault(row.currency, [])
            if len(items) < 3:
                items.append(row)
        return {
            currency: (
                items[0],
                items[1] if len(items) > 1 else None,
                items[2] if len(items) > 2 else None,
            )
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

    def list_rate_history_for_currencies(
        self,
        *,
        user_id: int,
        currencies: list[str],
        date_to: date,
    ) -> list[FxRateSnapshot]:
        normalized = [str(item or "").upper() for item in currencies if str(item or "").strip()]
        if not normalized:
            return []
        stmt = (
            select(FxRateSnapshot)
            .where(
                FxRateSnapshot.user_id == user_id,
                FxRateSnapshot.currency.in_(normalized),
                FxRateSnapshot.rate_date <= date_to,
            )
            .order_by(FxRateSnapshot.currency.asc(), FxRateSnapshot.rate_date.asc(), FxRateSnapshot.id.asc())
        )
        return list(self.db.scalars(stmt))

    def list_currency_preferences(self) -> list[UserPreference]:
        stmt = select(UserPreference).order_by(UserPreference.user_id.asc())
        return list(self.db.scalars(stmt))

    def list_active_plan_bank_requirements(self, *, user_id: int) -> list[tuple[str, str]]:
        stmt = (
            select(PlanOperation.fx_bank_code, PlanOperation.currency)
            .where(
                PlanOperation.user_id == user_id,
                PlanOperation.status == "active",
                PlanOperation.fx_rate_source == "bank",
                PlanOperation.fx_bank_code.is_not(None),
                PlanOperation.currency != PlanOperation.base_currency,
            )
            .distinct()
        )
        return [
            (str(bank_code).lower(), str(currency).upper())
            for bank_code, currency in self.db.execute(stmt).all()
            if bank_code and currency
        ]

    def get_latest_bank_rate_map(self) -> dict[tuple[str, str, str], FxBankRate]:
        rows = self.db.scalars(
            select(FxBankRate).order_by(
                FxBankRate.bank_code.asc(),
                FxBankRate.currency.asc(),
                FxBankRate.channel.asc(),
            )
        )
        return {
            (row.bank_code, row.currency, row.channel): row
            for row in rows
        }

    def list_bank_rates(
        self,
        *,
        bank_codes: list[str] | None = None,
        currencies: list[str] | None = None,
    ) -> list[FxBankRate]:
        stmt = select(FxBankRate)
        if bank_codes:
            stmt = stmt.where(FxBankRate.bank_code.in_(bank_codes))
        if currencies:
            stmt = stmt.where(FxBankRate.currency.in_(currencies))
        stmt = stmt.order_by(FxBankRate.bank_code.asc(), FxBankRate.currency.asc())
        return list(self.db.scalars(stmt))

    def get_bank_rate(
        self,
        *,
        bank_code: str,
        currency: str,
        base_currency: str,
        channel: str,
    ) -> FxBankRate | None:
        return self.db.scalar(
            select(FxBankRate).where(
                FxBankRate.bank_code == bank_code,
                FxBankRate.currency == currency,
                FxBankRate.base_currency == base_currency,
                FxBankRate.channel == channel,
            )
        )

    def upsert_bank_rate(
        self,
        *,
        bank_code: str,
        bank_name: str,
        currency: str,
        base_currency: str,
        scale: int,
        buy_rate,
        sell_rate,
        channel: str,
        location_name: str | None,
        source_url: str | None,
        quoted_at: datetime | None,
        fetched_at: datetime,
    ) -> FxBankRate:
        row = self.db.scalar(
            select(FxBankRate).where(
                FxBankRate.bank_code == bank_code,
                FxBankRate.currency == currency,
                FxBankRate.base_currency == base_currency,
                FxBankRate.channel == channel,
            )
        )
        if row is None:
            row = FxBankRate(
                bank_code=bank_code,
                currency=currency,
                base_currency=base_currency,
                channel=channel,
            )
            self.db.add(row)
        row.bank_name = bank_name
        row.scale = scale
        row.buy_rate = buy_rate
        row.sell_rate = sell_rate
        row.location_name = location_name
        row.source_url = source_url
        row.quoted_at = quoted_at
        row.fetched_at = fetched_at
        self.db.flush()
        return row

    def list_telegram_digest_targets(self) -> list:
        stmt = (
            select(AuthIdentity, UserPreference)
            .outerjoin(UserPreference, UserPreference.user_id == AuthIdentity.user_id)
            .where(AuthIdentity.provider == "telegram")
            .order_by(AuthIdentity.user_id.asc())
        )
        return list(self.db.execute(stmt).all())
