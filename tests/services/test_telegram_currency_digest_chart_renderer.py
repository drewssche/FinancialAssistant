from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO

import pytest
from PIL import Image

from app.services.telegram_currency_digest_chart_renderer import (
    CurrencyDigestChartPanel,
    CurrencyDigestChartPoint,
    CurrencyDigestChartSeries,
    TelegramCurrencyDigestChartPayload,
    TelegramCurrencyDigestChartRenderer,
)


AS_OF = date(2026, 8, 26)


def _points(
    *values: str | None,
    source_label: str | None = None,
) -> tuple[CurrencyDigestChartPoint, ...]:
    start = AS_OF - timedelta(days=6)
    return tuple(
        CurrencyDigestChartPoint(
            day=start + timedelta(days=index),
            value=Decimal(value) if value is not None else None,
            source_label=source_label,
        )
        for index, value in enumerate(values)
    )


def _panel(currency: str, display_label: str, offset: Decimal) -> CurrencyDigestChartPanel:
    return CurrencyDigestChartPanel(
        currency=currency,
        display_label=display_label,
        position_summary=f"Позиция 10,00 {currency}",
        series=(
            CurrencyDigestChartSeries(
                kind="nbrb",
                label="НБРБ",
                points=_points(
                    str(offset + Decimal("0.01")),
                    str(offset + Decimal("0.02")),
                    None,
                    str(offset + Decimal("0.04")),
                    str(offset + Decimal("0.03")),
                    str(offset + Decimal("0.05")),
                    str(offset + Decimal("0.06")),
                ),
            ),
            CurrencyDigestChartSeries(
                kind="bank_buy",
                label="Покупка банком",
                points=_points(*[str(offset - Decimal("0.02"))] * 7, source_label="Приорбанк"),
            ),
            CurrencyDigestChartSeries(
                kind="bank_sell",
                label="Продажа банком",
                points=_points(*[str(offset + Decimal("0.08"))] * 7, source_label="Технобанк"),
            ),
        ),
    )


def test_renderer_builds_compact_telegram_png_with_expected_metadata():
    payload = TelegramCurrencyDigestChartPayload(
        as_of=AS_OF,
        panels=(
            _panel("USD", "USD ($)", Decimal("3.20")),
            _panel("EUR", "EUR (€)", Decimal("3.50")),
            # The caller supplies the already scaled value for 100 RUB.
            _panel("RUB", "100 RUB (₽)", Decimal("3.58")),
        ),
        total_current_value=Decimal("765.43"),
        total_result_value=Decimal("12.34"),
    )

    content = TelegramCurrencyDigestChartRenderer().render(payload)

    assert content.startswith(b"\x89PNG\r\n\x1a\n")
    assert len(content) < 2_000_000
    with Image.open(BytesIO(content)) as image:
        assert image.size == (1080, 1350)
        assert image.mode == "RGB"
        assert image.info["Title"] == "Курсы валют за 7 дней"
        assert image.info["Period"] == "2026-08-20..2026-08-26"
        assert image.info["MissingData"] == "Values are not interpolated"
        assert image.getbbox() == (0, 0, 1080, 1350)


def test_renderer_does_not_connect_line_across_missing_day():
    period_start = AS_OF - timedelta(days=6)
    panel = CurrencyDigestChartPanel(
        currency="EUR",
        display_label="EUR (€)",
        series=(
            CurrencyDigestChartSeries(
                kind="bank_buy",
                label="Покупка банком",
                points=(
                    CurrencyDigestChartPoint(period_start, Decimal("3.40"), "Приорбанк"),
                    CurrencyDigestChartPoint(period_start + timedelta(days=2), Decimal("3.50"), "БСБ Банк"),
                ),
            ),
        ),
    )
    content = TelegramCurrencyDigestChartRenderer().render(
        TelegramCurrencyDigestChartPayload(as_of=AS_OF, panels=(panel,))
    )

    with Image.open(BytesIO(content)) as image:
        bank_buy_color = (94, 234, 212)
        missing_day_x = 240
        assert all(image.getpixel((missing_day_x, y)) != bank_buy_color for y in range(432, 555))


def test_renderer_marks_absent_series_as_missing_without_reusing_another_rate():
    renderer = TelegramCurrencyDigestChartRenderer()
    series = CurrencyDigestChartSeries(
        kind="nbrb",
        label="НБРБ",
        points=(CurrencyDigestChartPoint(AS_OF - timedelta(days=2), Decimal("3.25")),),
    )

    points = renderer._window_points(
        series,
        period_start=AS_OF - timedelta(days=6),
        period_end=AS_OF,
    )

    assert len(points) == 7
    assert points[-3][1] == Decimal("3.25")
    assert points[-2][1] is None
    assert points[-1][1] is None


def test_renderer_rejects_ambiguous_or_oversized_payloads():
    renderer = TelegramCurrencyDigestChartRenderer()
    duplicated = CurrencyDigestChartPanel(
        currency="USD",
        display_label="USD ($)",
        series=(
            CurrencyDigestChartSeries(kind="nbrb", label="НБРБ", points=()),
            CurrencyDigestChartSeries(kind="nbrb", label="НБРБ второй", points=()),
        ),
    )
    with pytest.raises(ValueError, match="Duplicate series"):
        renderer.render(TelegramCurrencyDigestChartPayload(as_of=AS_OF, panels=(duplicated,)))

    panel = _panel("USD", "USD ($)", Decimal("3.20"))
    with pytest.raises(ValueError, match="at most 4 panels"):
        renderer.render(TelegramCurrencyDigestChartPayload(as_of=AS_OF, panels=(panel,) * 5))


def test_renderer_rejects_missing_explicit_font(tmp_path):
    with pytest.raises(RuntimeError, match="font does not exist"):
        TelegramCurrencyDigestChartRenderer(font_path=tmp_path / "missing.ttf")
