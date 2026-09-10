import re


# Separators may decorate a chant, but letters and syllables must all be known.
# Keeping this list explicit prevents ordinary words from being accepted merely
# because they begin with a vocable such as "la" or "na".
_SEPARATOR_RE = re.compile(r"[\s♪♫♬・･~〜\-—–…,.!?！？、。()（）\[\]「」『』]+")
_LATIN_UNITS = ("yeah", "woo", "wow", "hey", "la", "na", "oh", "ah", "ha")
_SYLLABIC_UNITS = frozenset("ラらナな啦喔啊나라아오우")
_KNOWN_LEGACY_CHANTS = frozenset(
    {
        "タッタタラリラ",
        "ピーヒャラピーヒャラ",
        "ピーヒャラピー",
        "パッパパラパ",
    }
)


def _is_repeated_latin_vocable(compact: str) -> bool:
    lowered = compact.casefold()
    return any(
        lowered == unit * repetitions
        for unit in _LATIN_UNITS
        for repetitions in range(2, len(lowered) // len(unit) + 1)
    )


def _is_repeated_syllabic_vocable(compact: str) -> bool:
    return (
        len(compact) >= 2
        and len(set(compact)) == 1
        and compact[0] in _SYLLABIC_UNITS
    )


def looks_like_chant(text: str) -> bool:
    compact = _SEPARATOR_RE.sub("", text.strip())
    if not compact:
        return False
    return (
        compact in _KNOWN_LEGACY_CHANTS
        or _is_repeated_latin_vocable(compact)
        or _is_repeated_syllabic_vocable(compact)
    )
