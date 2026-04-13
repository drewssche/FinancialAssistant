from decimal import Decimal

from app.services.telegram_message_format import (
    ICON_INFO,
    ICON_TREND_DOWN,
    ICON_TREND_UP,
    signed_decimal,
    threshold_icon,
    title,
    trend_icon,
)


def test_title_prefixes_message_with_semantic_icon():
    assert title("⏰", "Скоро срок") == "⏰ Скоро срок"


def test_signed_decimal_uses_explicit_plus_and_minus():
    assert signed_decimal(Decimal("1.2345"), places=2) == "+1.23"
    assert signed_decimal(Decimal("-1.2345"), places=2) == "−1.23"
    assert signed_decimal(Decimal("0"), places=2) == "0.00"


def test_trend_icons_match_numeric_direction():
    assert trend_icon(Decimal("0.01")) == ICON_TREND_UP
    assert trend_icon(Decimal("-0.01")) == ICON_TREND_DOWN
    assert trend_icon(Decimal("0")) == ICON_INFO


def test_threshold_icons_match_alert_direction():
    assert threshold_icon("above") == ICON_TREND_UP
    assert threshold_icon("below") == ICON_TREND_DOWN
