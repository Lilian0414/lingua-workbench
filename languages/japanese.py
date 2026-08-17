from pykakasi import kakasi

from .common import looks_like_chant
from .japanese_numbers import romanize_arabic_numbers


class JapaneseLanguagePack:
    code = "ja"
    display_name = "日文"
    native_name = "日本語"
    html_lang = "ja"
    google_code = "ja"
    reading_label = "Hepburn 羅馬字"
    prompt_notes = "保留歌詞語氣、主詞省略與意象；無語意的吟唱可保留原文。"

    def __init__(self) -> None:
        self._converter = kakasi()

    def annotate(self, text: str) -> str:
        prepared = romanize_arabic_numbers(text)
        words = [item["hepburn"] for item in self._converter.convert(prepared)]
        return " ".join(" ".join(part for part in words if part).split())

    def should_preserve(self, text: str) -> bool:
        return looks_like_chant(text)
