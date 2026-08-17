import re


_DIGITS = "0123456789"
_DIGIT_WORDS = ["zero", "ichi", "ni", "san", "yon", "go", "roku", "nana", "hachi", "kyuu"]
_FULLWIDTH = str.maketrans("０１２３４５６７８９．，", "0123456789.,")


def _small_number(value: int) -> str:
    if value == 0:
        return "zero"
    parts: list[str] = []
    thousands, value = divmod(value, 1000)
    hundreds, value = divmod(value, 100)
    tens, ones = divmod(value, 10)
    if thousands:
        parts.append({1: "sen", 3: "sanzen", 8: "hassen"}.get(thousands, f"{_DIGIT_WORDS[thousands]}sen"))
    if hundreds:
        parts.append({1: "hyaku", 3: "sanbyaku", 6: "roppyaku", 8: "happyaku"}.get(hundreds, f"{_DIGIT_WORDS[hundreds]}hyaku"))
    if tens:
        parts.append("juu" if tens == 1 else f"{_DIGIT_WORDS[tens]}juu")
    if ones:
        parts.append(_DIGIT_WORDS[ones])
    return " ".join(parts)


def _integer(value: int) -> str:
    if value < 10_000:
        return _small_number(value)
    groups: list[str] = []
    oku, remainder = divmod(value, 100_000_000)
    man, remainder = divmod(remainder, 10_000)
    if oku:
        groups.append(f"{_integer(oku)}oku")
    if man:
        groups.append(f"{_small_number(man)}man")
    if remainder:
        groups.append(_small_number(remainder))
    return " ".join(groups)


def _plain_number(token: str) -> str:
    normalized = token.translate(_FULLWIDTH).replace(",", "")
    if "." in normalized:
        whole, fraction = normalized.split(".", 1)
        whole_text = _plain_number(whole or "0")
        fraction_text = " ".join(_DIGIT_WORDS[int(char)] for char in fraction if char in _DIGITS)
        return f"{whole_text} ten {fraction_text}".strip()
    if len(normalized) > 1 and normalized.startswith("0"):
        return " ".join(_DIGIT_WORDS[int(char)] for char in normalized)
    return _integer(int(normalized))


_DATES = {
    1: "tsuitachi", 2: "futsuka", 3: "mikka", 4: "yokka", 5: "itsuka",
    6: "muika", 7: "nanoka", 8: "youka", 9: "kokonoka", 10: "tooka",
    14: "juuyokka", 20: "hatsuka", 24: "nijuuyokka",
}


def _counter(value: int, suffix: str) -> str:
    if suffix == "月":
        return {4: "shigatsu", 7: "shichigatsu", 9: "kugatsu"}.get(value, f"{_integer(value)}gatsu")
    if suffix == "日":
        return _DATES.get(value, f"{_integer(value)}nichi")
    if suffix == "人":
        return {1: "hitori", 2: "futari"}.get(value, f"{_integer(value)}nin")
    if suffix == "歳":
        return {20: "hatachi"}.get(value, f"{_integer(value)}sai")
    if suffix == "時":
        return {4: "yoji", 7: "shichiji", 9: "kuji"}.get(value, f"{_integer(value)}ji")
    if suffix == "分":
        special = {1: "ippun", 3: "sanpun", 4: "yonpun", 6: "roppun", 8: "happun", 10: "juppun"}
        if value in special:
            return special[value]
        if value > 10 and value % 10 in special:
            tens = value - value % 10
            return f"{_integer(tens)} {special[value % 10]}"
        return f"{_integer(value)}fun"
    counters = {"年": "nen", "個": "ko", "回": "kai", "枚": "mai", "本": "hon"}
    return f"{_integer(value)}{counters.get(suffix, suffix)}"


_COUNTER_RE = re.compile(r"([0-9０-９][0-9０-９,，]*)(月|日|人|歳|才|時|分|年|個|回|枚|本)")
_NUMBER_RE = re.compile(r"[0-9０-９][0-9０-９,，]*(?:[.．][0-9０-９]+)?")


def romanize_arabic_numbers(text: str) -> str:
    """Replace Arabic numerals with common Japanese readings before kana conversion."""
    def replace_counter(match: re.Match[str]) -> str:
        value = int(match.group(1).translate(_FULLWIDTH).replace(",", ""))
        suffix = "歳" if match.group(2) == "才" else match.group(2)
        return f" {_counter(value, suffix)} "

    text = _COUNTER_RE.sub(replace_counter, text)
    return _NUMBER_RE.sub(lambda match: _plain_number(match.group(0)), text)
