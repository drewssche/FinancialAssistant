from datetime import date, datetime, timezone
from decimal import Decimal

from app.services.telegram_currency_digest_chart_data_service import (
    TelegramCurrencyDigestChartDataService,
)


def test_chart_data_uses_seven_days_scales_only_nbrb_rub_and_selects_best_bank_rates():
    as_of = date(2026, 8, 26)

    class _CurrencyService:
        def __init__(self):
            self.calls = []

        def get_rate_history(self, **kwargs):  # noqa: ANN003
            self.calls.append(kwargs)
            if kwargs["currency"] == "RUB":
                return [
                    {"rate_date": "2026-08-20", "rate": "0.035000"},
                    {"rate_date": "2026-08-26", "rate": "0.035600"},
                ]
            return [
                {"rate_date": "2026-08-20", "rate": "3.100000"},
                {"rate_date": "2026-08-26", "rate": "3.200000"},
            ]

    class _BankRateService:
        def __init__(self):
            self.calls = []

        def get_user_rate_history(self, **kwargs):  # noqa: ANN003
            self.calls.append(kwargs)
            if kwargs["currency"] == "RUB":
                return [
                    {
                        "rate_date": as_of,
                        "bank_name": "Приорбанк",
                        "buy_rate": "3.4500",
                        "sell_rate": "3.6200",
                    }
                ]
            return [
                {
                    "rate_date": as_of,
                    "bank_name": "Приорбанк",
                    "buy_rate": "3.1800",
                    "sell_rate": "3.2600",
                },
                {
                    "rate_date": as_of,
                    "bank_name": "Технобанк",
                    "buy_rate": "3.1900",
                    "sell_rate": "3.2400",
                },
            ]

    service = object.__new__(TelegramCurrencyDigestChartDataService)
    service.currency_service = _CurrencyService()
    service.bank_rate_service = _BankRateService()

    payload = service.build_payload(
        user_id=1,
        tracked_currencies=["USD", "RUB", "USD", "BYN"],
        bank_codes=["priorbank", "technobank"],
        overview={
            "base_currency": "BYN",
            "total_current_value": "100.50",
            "total_result_value": "5.25",
            "positions": [
                {"currency": "USD", "quantity": "10", "current_value": "32.00"},
            ],
        },
        as_of=as_of,
    )

    assert [panel.currency for panel in payload.panels] == ["USD", "RUB"]
    assert payload.panels[0].position_summary == "Позиция 10.00 USD · оценка 32.00 BYN"
    assert payload.panels[1].display_label == "100 RUB"
    rub_nbrb = next(series for series in payload.panels[1].series if series.kind == "nbrb")
    assert [point.value for point in rub_nbrb.points] == [Decimal("3.500000"), Decimal("3.560000")]
    rub_bank_buy = next(series for series in payload.panels[1].series if series.kind == "bank_buy")
    assert rub_bank_buy.points[-1].value == Decimal("3.4500")

    usd_bank_buy = next(series for series in payload.panels[0].series if series.kind == "bank_buy")
    usd_bank_sell = next(series for series in payload.panels[0].series if series.kind == "bank_sell")
    assert usd_bank_buy.points[-1].value == Decimal("3.1900")
    assert usd_bank_buy.points[-1].source_label == "Технобанк"
    assert usd_bank_sell.points[-1].value == Decimal("3.2400")
    assert usd_bank_sell.points[-1].source_label == "Технобанк"

    for call in service.currency_service.calls:
        assert call["date_from"] == date(2026, 8, 20)
        assert call["date_to"] == as_of
        assert call["sources"] == ("nbrb_auto_unit", "nbrb_history_unit")
    for call in service.bank_rate_service.calls:
        assert call["bank_codes"] == ["priorbank", "technobank"]
        assert call["date_from"] == date(2026, 8, 20)
        assert call["date_to"] == as_of


def test_chart_data_keeps_missing_bank_series_absent():
    class _CurrencyService:
        def get_rate_history(self, **kwargs):  # noqa: ANN003
            return [{"rate_date": kwargs["date_to"], "rate": "3.100000"}]

    class _BankRateService:
        def get_user_rate_history(self, **kwargs):  # noqa: ANN003
            return []

    service = object.__new__(TelegramCurrencyDigestChartDataService)
    service.currency_service = _CurrencyService()
    service.bank_rate_service = _BankRateService()

    payload = service.build_payload(
        user_id=1,
        tracked_currencies=["EUR"],
        bank_codes=[],
        overview={"base_currency": "BYN", "positions": []},
        as_of=date(2026, 8, 26),
    )

    assert [series.kind for series in payload.panels[0].series] == ["nbrb"]


def test_chart_data_normalizes_datetime_rows_to_calendar_dates():
    assert TelegramCurrencyDigestChartDataService._as_date(
        datetime(2026, 8, 26, 23, 45, tzinfo=timezone.utc)
    ) == date(2026, 8, 26)
