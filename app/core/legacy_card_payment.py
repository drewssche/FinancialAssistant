"""Translate a historical card charge into an expense at its recorded exchange rate."""
from decimal import Decimal, ROUND_HALF_UP


def payment_valuation(operation, trade, *, has_receipt):
    base = operation["base_currency"]
    currency = trade["asset_currency"]
    amount = Decimal(str(operation["amount"]))
    paid = Decimal(str(trade["quantity"]))
    rate = Decimal(str(trade["unit_price"]))
    cents = Decimal("0.01")
    if (currency == base or operation["kind"] != "expense" or trade["side"] != "sell"
            or trade["quote_currency"] != base or paid <= 0 or rate <= 0
            or paid != paid.quantize(cents)
            or (paid * rate).quantize(cents, rounding=ROUND_HALF_UP) != amount):
        raise ValueError("Historical card charge cannot be reconciled to its expense")
    same_payment = operation["currency"] == currency and Decimal(str(operation["original_amount"])) == paid
    if same_payment and operation.get("fx_rate") is not None and Decimal(str(operation["fx_rate"])) == rate:
        values = {"fx_payment_mode": "valuation"}
        if not operation.get("fx_rate_date"):
            values["fx_rate_date"] = trade["trade_date"]
        return values
    if not same_payment and operation["currency"] != base:
        raise ValueError("Historical charge and receipt use two different foreign currencies")
    return {
        "currency": currency, "original_amount": paid, "fx_rate": rate,
        "receipt_currency": base if has_receipt and operation["currency"] == base else None,
        "fx_rate_source": "manual", "fx_rate_date": trade["trade_date"],
        "fx_bank_code": None, "fx_bank_name": None, "fx_bank_channel": None,
        "fx_rate_kind": None, "fx_quoted_at": None, "fx_fetched_at": None, "fx_rate_stale": False,
        "fx_rate_scale": 100 if currency == "RUB" else 1, "fx_payment_mode": "valuation",
    }
