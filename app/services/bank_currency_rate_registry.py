from __future__ import annotations


BANK_RATE_PROVIDERS = {
    "priorbank": {
        "name": "Приорбанк",
        "channel": "online",
        "channel_label": "онлайн",
    },
    "technobank": {
        "name": "Технобанк",
        "channel": "cash",
        "channel_label": "наличные",
    },
    "bsb": {
        "name": "БСБ Банк",
        "channel": "cash",
        "channel_label": "наличные",
    },
    "sber": {
        "name": "Сбер Банк",
        "channel": "cash",
        "channel_label": "наличные",
    },
}

DEFAULT_BANK_RATE_BANKS = list(BANK_RATE_PROVIDERS)
BANK_RATE_REFRESH_MINUTES = 15
BANK_RATE_STALE_MINUTES = 45


def display_scale(currency: str) -> int:
    return 100 if str(currency or "").strip().upper() == "RUB" else 1

