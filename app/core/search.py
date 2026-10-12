"""Literal substring search with optional RU/EN keyboard-layout correction.

Keep this contract in sync with static/js/app-search-utils.js. Stored identities
and the user's input are never changed by these presentation/search helpers.
"""

EN_KEYS = "`qwertyuiop[]asdfghjkl;'zxcvbnm,."
RU_KEYS = "ёйцукенгшщзхъфывапролджэячсмитьбю"
EN_TO_RU = str.maketrans(EN_KEYS + '~{}:"<>', RU_KEYS + "ёхъжэбю")
RU_TO_EN = str.maketrans(RU_KEYS, EN_KEYS)


def normalize_search(value: str | None) -> str:
    return " ".join((value or "").lower().replace("ё", "е").split())


def search_variants(query: str | None) -> tuple[str, ...]:
    raw = (query or "").lower()
    variants = [normalize_search(raw)]
    if any("a" <= char <= "z" for char in raw):
        variants.append(normalize_search(raw.translate(EN_TO_RU)))
    if any("а" <= char <= "я" or char == "ё" for char in raw):
        variants.append(normalize_search(raw.translate(RU_TO_EN)))
    return tuple(dict.fromkeys(variants))


def search_rank(value: str | None, query: str | None) -> int:
    text = normalize_search(value)
    variants = search_variants(query)
    return next((index for index, variant in enumerate(variants) if variant in text), len(variants))


def matches_search(value: str | None, query: str | None) -> bool:
    return search_rank(value, query) < len(search_variants(query))
