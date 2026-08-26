from datetime import date, datetime

from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as postgresql_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import Session

from app.db.models import (
    AuthIdentity,
    FxBankRate,
    FxBankRateSnapshot,
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
            select(FxBankRate)
            .where(
                FxBankRate.bank_code == bank_code,
                FxBankRate.currency == currency,
                FxBankRate.base_currency == base_currency,
                FxBankRate.channel == channel,
            )
            .execution_options(populate_existing=True)
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
        values = {
            "bank_code": bank_code,
            "bank_name": bank_name,
            "currency": currency,
            "base_currency": base_currency,
            "scale": scale,
            "buy_rate": buy_rate,
            "sell_rate": sell_rate,
            "channel": channel,
            "location_name": location_name,
            "source_url": source_url,
            "quoted_at": quoted_at,
            "fetched_at": fetched_at,
        }
        self._execute_atomic_upsert(
            model=FxBankRate,
            values=values,
            conflict_columns=("bank_code", "currency", "base_currency", "channel"),
        )
        self.db.flush()
        row = self.db.scalar(
            select(FxBankRate)
            .where(
                FxBankRate.bank_code == bank_code,
                FxBankRate.currency == currency,
                FxBankRate.base_currency == base_currency,
                FxBankRate.channel == channel,
            )
            .execution_options(populate_existing=True)
        )
        if row is None:  # pragma: no cover - defensive guard for unsupported database dialects
            raise RuntimeError("Bank rate upsert did not return a row")
        return row

    def upsert_bank_rate_snapshot(
        self,
        *,
        bank_code: str,
        bank_name: str,
        currency: str,
        base_currency: str,
        rate_date: date,
        scale: int,
        buy_rate,
        sell_rate,
        channel: str,
        location_name: str | None,
        source_url: str | None,
        quoted_at: datetime | None,
        fetched_at: datetime,
    ) -> FxBankRateSnapshot:
        values = {
            "bank_code": bank_code,
            "bank_name": bank_name,
            "currency": currency,
            "base_currency": base_currency,
            "rate_date": rate_date,
            "scale": scale,
            "buy_rate": buy_rate,
            "sell_rate": sell_rate,
            "channel": channel,
            "location_name": location_name,
            "source_url": source_url,
            "quoted_at": quoted_at,
            "fetched_at": fetched_at,
        }
        self._execute_atomic_upsert(
            model=FxBankRateSnapshot,
            values=values,
            conflict_columns=("bank_code", "currency", "base_currency", "channel", "rate_date"),
        )
        self.db.flush()
        row = self.db.scalar(
            select(FxBankRateSnapshot)
            .where(
                FxBankRateSnapshot.bank_code == bank_code,
                FxBankRateSnapshot.currency == currency,
                FxBankRateSnapshot.base_currency == base_currency,
                FxBankRateSnapshot.channel == channel,
                FxBankRateSnapshot.rate_date == rate_date,
            )
            .execution_options(populate_existing=True)
        )
        if row is None:  # pragma: no cover - defensive guard for unsupported database dialects
            raise RuntimeError("Bank rate history upsert did not return a row")
        return row

    def _execute_atomic_upsert(
        self,
        *,
        model,
        values: dict,
        conflict_columns: tuple[str, ...],
    ) -> None:
        dialect_name = self.db.get_bind().dialect.name
        if dialect_name == "postgresql":
            statement = postgresql_insert(model).values(**values)
        elif dialect_name == "sqlite":
            statement = sqlite_insert(model).values(**values)
        else:  # pragma: no cover - production and tests use PostgreSQL/SQLite
            raise RuntimeError(f"Bank rate upsert is unsupported for database dialect: {dialect_name}")
        update_values = {
            key: getattr(statement.excluded, key)
            for key in values
            if key not in conflict_columns
        }
        self.db.execute(
            statement.on_conflict_do_update(
                index_elements=list(conflict_columns),
                set_=update_values,
                where=statement.excluded.fetched_at >= model.fetched_at,
            )
        )

    def list_bank_rate_history(
        self,
        *,
        bank_codes: list[str],
        currency: str,
        base_currency: str = "BYN",
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[FxBankRateSnapshot]:
        if not bank_codes:
            return []
        stmt = select(FxBankRateSnapshot).where(
            FxBankRateSnapshot.bank_code.in_(bank_codes),
            FxBankRateSnapshot.currency == currency,
            FxBankRateSnapshot.base_currency == base_currency,
        )
        if date_from is not None:
            stmt = stmt.where(FxBankRateSnapshot.rate_date >= date_from)
        if date_to is not None:
            stmt = stmt.where(FxBankRateSnapshot.rate_date <= date_to)
        stmt = stmt.order_by(
            FxBankRateSnapshot.rate_date.asc(),
            FxBankRateSnapshot.bank_code.asc(),
            FxBankRateSnapshot.channel.asc(),
            FxBankRateSnapshot.id.asc(),
        )
        return list(self.db.scalars(stmt))

    def list_telegram_digest_targets(self) -> list:
        stmt = (
            select(AuthIdentity, UserPreference)
            .outerjoin(UserPreference, UserPreference.user_id == AuthIdentity.user_id)
            .where(AuthIdentity.provider == "telegram")
            .order_by(AuthIdentity.user_id.asc())
        )
        return list(self.db.execute(stmt).all())
