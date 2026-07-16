from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ActivityEvent, Category, CategoryGroup, DebtCounterparty
from app.repositories.activity_repo import ActivityRepository


class ActivityService:
    ENUM_LABELS = {
        "kind": {
            "expense": "Расход",
            "income": "Доход",
        },
        "direction": {
            "lend": "Я дал",
            "borrow": "Я взял",
        },
        "closure_reason": {
            "repaid": "Погашен",
            "forgiven": "Прощен",
        },
        "status": {
            "active": "Активен",
            "confirmed": "Подтвержден",
            "skipped": "Пропущен",
            "cancelled": "Отменен",
        },
        "recurrence_frequency": {
            "daily": "Ежедневно",
            "weekly": "Еженедельно",
            "monthly": "Ежемесячно",
            "yearly": "Ежегодно",
        },
        "side": {
            "buy": "Покупка",
            "sell": "Продажа",
        },
        "trade_kind": {
            "manual": "Ручная сделка",
            "card_payment": "Оплата картой",
        },
    }
    MONEY_FIELDS = {"amount", "original_amount", "principal", "fee"}
    RATE_FIELDS = {"fx_rate", "unit_price"}
    DATE_FIELDS = {"operation_date", "start_date", "due_date", "scheduled_date", "recurrence_end_date", "last_used_at", "trade_date"}
    REFERENCE_FIELDS = {"category_id", "last_category_id", "group_id", "counterparty_id"}

    def __init__(self, db: Session):
        self.db = db
        self.repo = ActivityRepository(db)

    @staticmethod
    def _raw(value: Any) -> Any:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return value

    @classmethod
    def _display(cls, value: Any, field: str | None = None) -> str:
        if value is None:
            return "Не задано"
        if field in cls.ENUM_LABELS:
            normalized = str(value)
            return cls.ENUM_LABELS[field].get(normalized, normalized)
        if field in cls.MONEY_FIELDS:
            return cls._format_decimal(value, digits=2)
        if field in cls.RATE_FIELDS:
            return cls._format_decimal(value, digits=6)
        if field in cls.DATE_FIELDS:
            return cls._format_date(value)
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, (date, datetime)):
            return cls._format_date(value)
        if isinstance(value, bool):
            return "Да" if value else "Нет"
        return str(value)

    @staticmethod
    def _format_decimal(value: Any, *, digits: int) -> str:
        try:
            number = Decimal(str(value))
        except Exception:
            return str(value)
        quant = Decimal("1").scaleb(-digits)
        text = f"{number.quantize(quant):f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text

    @staticmethod
    def _format_date(value: Any) -> str:
        if value is None:
            return "Не задано"
        if isinstance(value, datetime):
            value = value.date()
        if isinstance(value, date):
            return value.strftime("%d.%m.%Y")
        raw = str(value)
        try:
            return date.fromisoformat(raw[:10]).strftime("%d.%m.%Y")
        except Exception:
            return raw

    @classmethod
    def snapshot(cls, obj: Any, fields: list[str]) -> dict:
        return {field: cls._raw(getattr(obj, field, None)) for field in fields}

    @classmethod
    def build_changes(cls, before: dict, after: dict, labels: dict[str, str]) -> list[dict]:
        changes: list[dict] = []
        for field, label in labels.items():
            old = before.get(field)
            new = after.get(field)
            if old == new:
                continue
            changes.append(
                {
                    "field": field,
                    "label": label,
                    "old": old,
                    "new": new,
                    "old_display": cls._display(old, field),
                    "new_display": cls._display(new, field),
                }
            )
        return changes

    def record(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
        event_type: str,
        title: str,
        actor_user_id: int | None = None,
        changes: list[dict] | None = None,
        metadata: dict | None = None,
        source: str = "web",
        created_at: datetime | None = None,
    ) -> ActivityEvent | None:
        event = ActivityEvent(
            user_id=user_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type=event_type,
            title=title,
            changes_json=changes or [],
            metadata_json=metadata or {},
            source=source,
        )
        if created_at is not None:
            event.created_at = created_at
        return self.repo.create(event)

    def record_created(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
        title: str,
        actor_user_id: int | None = None,
        metadata: dict | None = None,
        source: str = "web",
        created_at: datetime | None = None,
    ) -> ActivityEvent | None:
        return self.record(
            user_id=user_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type="created",
            title=title,
            metadata=metadata,
            source=source,
            created_at=created_at,
        )

    def record_updated(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
        before: dict,
        after: dict,
        labels: dict[str, str],
        title: str = "Изменения сохранены",
        actor_user_id: int | None = None,
        metadata: dict | None = None,
        source: str = "web",
    ) -> ActivityEvent | None:
        changes = self.build_changes(before, after, labels)
        if not changes:
            return None
        return self.record(
            user_id=user_id,
            actor_user_id=actor_user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type="updated",
            title=title,
            changes=changes,
            metadata=metadata,
            source=source,
        )

    def list_for_entity(self, *, user_id: int, entity_type: str, entity_id: int, page: int = 1, page_size: int = 50) -> tuple[list[dict], int]:
        items, total = self.repo.list_for_entity(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return [self._serialize(row) for row in items], total

    def list_recent(self, *, user_id: int, page: int = 1, page_size: int = 50) -> tuple[list[dict], int]:
        items, total = self.repo.list_recent_for_user(
            user_id=user_id,
            limit=page_size,
            offset=(page - 1) * page_size,
        )
        return [self._serialize(row) for row in items], total

    def _serialize(self, row: ActivityEvent) -> dict:
        metadata = {
            key: value
            for key, value in (row.metadata_json or {}).items()
            if not str(key).startswith("_")
        }
        return {
            "id": int(row.id),
            "user_id": int(row.user_id),
            "actor_user_id": int(row.actor_user_id) if row.actor_user_id is not None else None,
            "entity_type": row.entity_type,
            "entity_id": int(row.entity_id),
            "event_type": row.event_type,
            "title": row.title,
            "changes": [self._serialize_change(change, row) for change in (row.changes_json or [])],
            "metadata": metadata,
            "metadata_display": self._metadata_display(metadata),
            "source": row.source,
            "created_at": row.created_at,
        }

    def get_restore_event(
        self,
        *,
        user_id: int,
        entity_type: str,
        entity_id: int,
    ) -> ActivityEvent:
        event = self.repo.get_latest_for_entity(
            user_id=user_id,
            entity_type=entity_type,
            entity_id=entity_id,
            event_type="deleted",
            for_update=True,
        )
        if event is None:
            raise LookupError("Restore snapshot not found")
        metadata = event.metadata_json if isinstance(event.metadata_json, dict) else {}
        if metadata.get("_restored_entity_id") is not None:
            raise ValueError("Entity has already been restored")
        if not isinstance(metadata.get("_restore_snapshot"), dict):
            raise ValueError("Deleted entity does not have a restorable snapshot")
        return event

    @staticmethod
    def mark_restored(event: ActivityEvent, *, entity_id: int) -> None:
        metadata = dict(event.metadata_json or {})
        metadata["_restored_entity_id"] = int(entity_id)
        metadata["_restored_at"] = datetime.now().astimezone().isoformat()
        event.metadata_json = metadata

    @staticmethod
    def _metadata_display(metadata: dict) -> list[str]:
        if not isinstance(metadata, dict):
            return []
        items: list[str] = []
        if metadata.get("receipt_updated") is True:
            receipt_changes = metadata.get("receipt_changes") if isinstance(metadata.get("receipt_changes"), dict) else {}
            added = int(receipt_changes.get("added_count") or 0)
            removed = int(receipt_changes.get("removed_count") or 0)
            changed = int(receipt_changes.get("changed_count") or 0)
            if added or removed or changed:
                parts = []
                if added:
                    parts.append(f"добавлено {added}")
                if removed:
                    parts.append(f"удалено {removed}")
                if changed:
                    parts.append(f"изменено {changed}")
                items.append(f"Чек: {', '.join(parts)}")
                for label, names in (
                    ("Добавлено", receipt_changes.get("added")),
                    ("Удалено", receipt_changes.get("removed")),
                    ("Изменено", receipt_changes.get("changed")),
                ):
                    visible_names = [str(name) for name in (names or []) if name][:3]
                    if visible_names:
                        items.append(f"{label}: {', '.join(visible_names)}")
            else:
                items.append("Чек обновлен")
        if metadata.get("fx_settlement_updated") is True:
            items.append("Валютная оплата обновлена")
        message_type = metadata.get("message_type")
        if message_type == "plan_reminder":
            items.append("Напоминание по плану отправлено")
        elif message_type == "debt_reminder":
            items.append("Напоминание по долгу отправлено")
        elif message_type == "currency_digest":
            items.append("Валютная сводка отправлена")
        elif message_type == "currency_alert":
            items.append("Валютное уведомление отправлено")
        return items

    @classmethod
    def summarize_receipt_changes(cls, before: list[Any] | None, after: list[Any] | None) -> dict:
        before_map = cls._receipt_item_map(before or [])
        after_map = cls._receipt_item_map(after or [])
        added_keys = [key for key in after_map if key not in before_map]
        removed_keys = [key for key in before_map if key not in after_map]
        changed_keys = [
            key
            for key in after_map
            if key in before_map and cls._receipt_compare_payload(after_map[key]) != cls._receipt_compare_payload(before_map[key])
        ]
        return {
            "added": [after_map[key]["name"] for key in added_keys],
            "removed": [before_map[key]["name"] for key in removed_keys],
            "changed": [after_map[key]["name"] for key in changed_keys],
            "added_count": len(added_keys),
            "removed_count": len(removed_keys),
            "changed_count": len(changed_keys),
        }

    @classmethod
    def _receipt_item_map(cls, rows: list[Any]) -> dict[str, dict]:
        result: dict[str, dict] = {}
        for index, row in enumerate(rows):
            payload = cls._receipt_item_payload(row)
            key = payload.get("template_id") or f"{payload.get('shop_name', '').casefold()}|{payload.get('name', '').casefold()}|{index}"
            result[str(key)] = payload
        return result

    @staticmethod
    def _receipt_item_payload(row: Any) -> dict:
        get = row.get if isinstance(row, dict) else lambda key, default=None: getattr(row, key, default)
        return {
            "template_id": get("template_id"),
            "category_id": get("category_id"),
            "shop_name": str(get("shop_name") or ""),
            "name": str(get("name") or "Без названия"),
            "quantity": str(get("quantity") or "0"),
            "unit_price": str(get("unit_price") or "0"),
            "line_total": str(get("line_total") or "0"),
            "is_discounted": bool(get("is_discounted") or False),
            "regular_unit_price": str(get("regular_unit_price") or ""),
            "discount_type": str(get("discount_type") or ""),
            "note": str(get("note") or ""),
        }

    @staticmethod
    def _receipt_compare_payload(payload: dict) -> tuple:
        return (
            payload.get("category_id"),
            payload.get("shop_name"),
            payload.get("name"),
            payload.get("quantity"),
            payload.get("unit_price"),
            payload.get("line_total"),
            payload.get("is_discounted"),
            payload.get("regular_unit_price"),
            payload.get("discount_type"),
            payload.get("note"),
        )

    def _serialize_change(self, change: dict, row: ActivityEvent) -> dict:
        if not isinstance(change, dict):
            return change
        payload = dict(change)
        field = str(payload.get("field") or "")
        if field in self.REFERENCE_FIELDS:
            payload["old_display"] = self._resolve_reference_display(field, payload.get("old"), row)
            payload["new_display"] = self._resolve_reference_display(field, payload.get("new"), row)
            return payload
        payload["old_display"] = self._display(payload.get("old"), field)
        payload["new_display"] = self._display(payload.get("new"), field)
        return payload

    def _resolve_reference_display(self, field: str, value: Any, row: ActivityEvent) -> str:
        if value in (None, ""):
            return "Не задано"
        try:
            entity_id = int(value)
        except (TypeError, ValueError):
            return str(value)
        if entity_id <= 0:
            return "Не задано"
        if field in {"category_id", "last_category_id"}:
            item = self.db.get(Category, entity_id)
            return item.name if item else f"Категория #{entity_id} (удалена)"
        if field == "group_id":
            item = self.db.get(CategoryGroup, entity_id)
            return item.name if item else f"Группа #{entity_id} (удалена)"
        if field == "counterparty_id":
            item = self.db.scalar(
                select(DebtCounterparty).where(
                    DebtCounterparty.user_id == row.user_id,
                    DebtCounterparty.id == entity_id,
                )
            )
            return item.name if item else f"Контрагент #{entity_id} (удален)"
        return str(value)
