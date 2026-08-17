from collections.abc import Callable

from koroman import romanize

from .common import looks_like_chant


class KoreanLanguagePack:
    code = "ko"
    display_name = "韓文"
    native_name = "한국어"
    html_lang = "ko"
    google_code = "ko"
    reading_label = "韓文羅馬字（修訂式）"
    prompt_notes = "保留敬語層次、主詞省略與歌詞意象；無語意的吟唱可保留原文。"

    def __init__(self, romanizer: Callable[..., str] = romanize) -> None:
        self._romanizer = romanizer

    def annotate(self, text: str) -> str:
        try:
            return self._romanizer(
                text,
                use_pronunciation_rules=True,
                casing_option="lowercase",
            ).strip()
        except TypeError:
            return self._romanizer(text).strip()

    def should_preserve(self, text: str) -> bool:
        return looks_like_chant(text)
