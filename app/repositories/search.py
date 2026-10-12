"""Search expressions: filtering and relevance happen before LIMIT/OFFSET."""

import re
import sqlite3

from sqlalchemy import Boolean, String, case, event, literal, or_, true
from sqlalchemy.engine import Engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.functions import FunctionElement

from app.core.search import matches_search, normalize_search, search_variants


class search_text_match(FunctionElement):
    type = Boolean()
    inherit_cache = True


@compiles(search_text_match, "postgresql")
def _postgres_match(element, compiler, **kw):
    column, pattern, _query, _original = list(element.clauses)
    # One bound, precomputed regex per predicate; do not repeatedly normalize
    # every value in correlated receipt/catalog subqueries.
    return f"(coalesce({compiler.process(column, **kw)}, '') ~ {compiler.process(pattern, **kw)})"


@compiles(search_text_match, "sqlite")
def _sqlite_match(element, compiler, **kw):
    column, _pattern, query, original = list(element.clauses)
    args = ', '.join(compiler.process(value, **kw) for value in (column, query, original))
    return f"fa_search_matches({args})"


@event.listens_for(Engine, "connect")
def _register_sqlite_matcher(connection, _record):
    # SQLite has no built-in Unicode case folding or PostgreSQL regex operator.
    if isinstance(connection, sqlite3.Connection):
        connection.create_function(
            "fa_search_matches", 3,
            lambda value, query, original: (
                normalize_search(query) in normalize_search(value)
                if original else matches_search(value, query)
            ),
            deterministic=True,
        )


def _literal_pattern(variant: str) -> str:
    parts = []
    for char in variant:
        if char == "е":
            parts.append("[еёЕЁ]")
        elif char == " ":
            parts.append("[[:space:] ]+")
        elif len(char.upper()) == 1 and char.upper() != char:
            # Explicit classes also support Cyrillic in PostgreSQL's C locale.
            parts.append(f"[{re.escape(char)}{re.escape(char.upper())}]")
        else:
            parts.append(re.escape(char))
    return "".join(parts)


def search_match(column, query: str | None, *, original_only: bool = False):
    variants = search_variants(query)
    if not variants[0]:
        return true()
    pattern = "|".join(_literal_pattern(variant) for variant in (variants[:1] if original_only else variants))
    return search_text_match(column, literal(pattern, String()), literal(query, String()), literal(original_only))


def search_any(query: str | None, *columns, original_only: bool = False):
    return or_(*(search_match(column, query, original_only=original_only) for column in columns))


def search_order(query: str | None, *columns, predicate=None):
    if len(search_variants(query)) < 2:
        return []
    original = predicate if predicate is not None else search_any(query, *columns, original_only=True)
    return [case((original, 0), else_=1)]
