from __future__ import annotations

from decimal import Decimal


ICON_INFO = "ℹ️"
ICON_REMINDER = "⏰"
ICON_WARNING = "⚠️"
ICON_SUCCESS = "✅"
ICON_MONEY_IN = "💰"
ICON_MONEY_OUT = "💸"
ICON_TREND_UP = "📈"
ICON_TREND_DOWN = "📉"
ICON_TARGET = "🎯"
ICON_RECEIPT = "🧾"
ICON_ADMIN = "🛠️"
ICON_ACCESS = "🛂"
ICON_CURRENCY = "💱"


def title(icon: str, text: str) -> str:
    return f"{icon} {text}"


def signed_decimal(value, *, places: int = 2) -> str:
    amount = Decimal(value or 0)
    sign = "+" if amount > 0 else "−" if amount < 0 else ""
    return f"{sign}{abs(amount):.{places}f}"


def trend_icon(value) -> str:
    amount = Decimal(value or 0)
    if amount > 0:
        return ICON_TREND_UP
    if amount < 0:
        return ICON_TREND_DOWN
    return ICON_INFO


def threshold_icon(direction: str) -> str:
    return ICON_TREND_UP if direction == "above" else ICON_TREND_DOWN


def money_direction_icon(kind: str) -> str:
    return ICON_MONEY_IN if kind == "income" else ICON_MONEY_OUT
