import base64
from datetime import datetime, timezone
from decimal import Decimal
import json

from app.services.bank_currency_rate_refresh_service import BankCurrencyRateRefreshService


def test_parse_priorbank_online_rates():
    payload = {
        "resultEBank": json.dumps(
            {
                "simpleCurrencyList": [
                    {
                        "baseCurrency": 840,
                        "baseCurrencyNominal": 1,
                        "ratedCurrency": 933,
                        "buyRate": "3.0100",
                        "sellRate": "3.0700",
                        "validFromDate": "18.08.2026",
                        "validFromTime": "10:30",
                    },
                    {
                        "baseCurrency": 643,
                        "baseCurrencyNominal": 100,
                        "ratedCurrency": 933,
                        "buyRate": "3.5000",
                        "sellRate": "3.6500",
                    },
                ]
            }
        )
    }

    quotes = BankCurrencyRateRefreshService._parse_priorbank(payload)

    assert [(item.currency, item.scale) for item in quotes] == [("USD", 1), ("RUB", 100)]
    assert quotes[0].buy_rate == Decimal("3.010000")
    assert quotes[0].sell_rate == Decimal("3.070000")
    assert quotes[0].channel == "online"


def test_parse_technobank_cash_rates():
    raw = {
        "items": [
            {
                "cityId": 37,
                "title": "ЦБУ",
                "address": "Минск",
                "exchangeRates": [
                    {
                        "currency": "EUR",
                        "quantity": 1,
                        "buying": {"value": "3.4200"},
                        "sale": {"value": "3.5100"},
                    },
                    {
                        "currency": "CNY",
                        "quantity": 10,
                        "buying": {"value": "4.4500"},
                        "sale": {"value": "4.6500"},
                    },
                ],
            }
        ]
    }
    payload = {"encoded": base64.b64encode(json.dumps(raw).encode()).decode()}

    quotes = BankCurrencyRateRefreshService._parse_technobank(payload)

    assert len(quotes) == 2
    assert quotes[0].currency == "EUR"
    assert quotes[0].location_name == "ЦБУ · Минск"
    assert quotes[0].buy_rate == Decimal("3.420000")
    assert quotes[1].currency == "CNY"
    assert quotes[1].scale == 1
    assert quotes[1].buy_rate == Decimal("0.445000")


def test_parse_bsb_cash_rates():
    payload = {
        "fromTime": 1787047200000,
        "rates": [
            {
                "buyCurrencyName": "RUB",
                "sellCurrencyName": "BYN",
                "buyCurrencyScale": 100,
                "scaledBuyAmount": "3.4800",
                "scaledSellAmount": "3.6200",
            }
        ],
    }

    quotes = BankCurrencyRateRefreshService._parse_bsb(payload)

    assert len(quotes) == 1
    assert quotes[0].currency == "RUB"
    assert quotes[0].scale == 100
    assert quotes[0].quoted_at == datetime.fromtimestamp(1787047200, tz=timezone.utc)


def test_parse_sber_selects_best_cash_buy_and_sell():
    payload = {
        "rates": [
            {
                "sourceCurrency": "USD",
                "targetCurrency": "BYN",
                "direction": "buy",
                "exchangeRate": "3.0100",
                "scaleCurrency": 1,
                "branchName": "Офис 1",
            },
            {
                "sourceCurrency": "USD",
                "targetCurrency": "BYN",
                "direction": "buy",
                "exchangeRate": "3.0200",
                "scaleCurrency": 1,
                "branchName": "Офис 2",
            },
            {
                "sourceCurrency": "USD",
                "targetCurrency": "BYN",
                "direction": "sell",
                "exchangeRate": "3.0900",
                "scaleCurrency": 1,
            },
            {
                "sourceCurrency": "USD",
                "targetCurrency": "BYN",
                "direction": "sell",
                "exchangeRate": "3.0800",
                "scaleCurrency": 1,
            },
        ]
    }

    quotes = BankCurrencyRateRefreshService._parse_sber(payload)

    assert len(quotes) == 1
    assert quotes[0].buy_rate == Decimal("3.020000")
    assert quotes[0].sell_rate == Decimal("3.080000")
    assert quotes[0].location_name == "Офис 2"
