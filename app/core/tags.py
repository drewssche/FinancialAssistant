"""Purpose tags shared by catalog defaults and dated purchase snapshots."""
from unicodedata import normalize

from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator


def normalize_tags(values):
    tags = []
    for value in values or ():
        name = " ".join(normalize("NFC", value).strip().lstrip("#").split()).casefold()
        if not name:
            continue
        if "," in name or "#" in name or len(name) > 48:
            raise ValueError("Тег должен содержать до 48 символов без запятых и знака #")
        if name not in tags:
            tags.append(name)
    return tags


class TagList(TypeDecorator):
    """Searchable Unicode text on both PostgreSQL and SQLite."""
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return ", ".join("#" + name for name in normalize_tags(value))

    def process_result_value(self, value, dialect):
        return [name.removeprefix("#") for name in value.split(", ")] if value else []


def preserve_receipt_tags(incoming, previous):
    """Older editors omit tags. Restore the snapshot for a matching receipt line."""
    for item in incoming:
        if "tags" in item:
            continue
        matches = [row for row in previous if (
            row.template_id == item.get("template_id") and row.template_id is not None
            or (row.name, row.shop_name or "") == (item.get("name"), item.get("shop_name") or "")
        )]
        snapshots = {tuple(row.tags or ()) for row in matches}
        if len(snapshots) > 1:
            raise ValueError("Обновите страницу, чтобы сохранить разные теги у одинаковых позиций.")
        if snapshots:
            item["tags"] = list(snapshots.pop())
