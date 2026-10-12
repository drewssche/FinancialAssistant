"""Search expressions: filtering and relevance happen before LIMIT/OFFSET."""

import sqlite3

from sqlalchemy import String, case, event, or_, true
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement

from app.core.search import normalize_search, search_variants


class normalized_search_text(FunctionElement):
    type = String()
    inherit_cache = True


@compiles(normalized_search_text, "postgresql")
def _postgres_normalized(element, compiler, **kw):
    column = compiler.process(list(element.clauses)[0], **kw)
    # Explicit Cyrillic folding also works in databases initialized with C locale.
    upper = "АБВГДЕЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯЁё"
    lower = "абвгдежзийклмнопрстуфхцчшщъыьэюяее"
    return f"trim(regexp_replace(translate(lower(coalesce({column}, '')), '{upper}', '{lower}'), '[[:space:] ]+', ' ', 'g'))"


@compiles(normalized_search_text, "sqlite")
def _sqlite_normalized(element, compiler, **kw):
    return f"fa_search_normalize({compiler.process(list(element.clauses)[0], **kw)})"


@event.listens_for(Engine, "connect")
def _register_sqlite_normalizer(connection, _record):
    # SQLite lower() is ASCII-only. Local/test databases need the same contract.
    if isinstance(connection, sqlite3.Connection):
        connection.create_function("fa_search_normalize", 1, normalize_search, deterministic=True)


def search_match(column, query: str | None, *, original_only: bool = False):
    variants = search_variants(query)
    if not variants[0]:
        return true()
    return or_(*(
        normalized_search_text(column).contains(variant, autoescape=True)
        for variant in (variants[:1] if original_only else variants)
    ))


def search_any(query: str | None, *columns, original_only: bool = False):
    return or_(*(search_match(column, query, original_only=original_only) for column in columns))


def search_order(query: str | None, *columns, predicate=None):
    if len(search_variants(query)) < 2:
        return []
    original = predicate if predicate is not None else search_any(query, *columns, original_only=True)
    return [case((original, 0), else_=1)]
