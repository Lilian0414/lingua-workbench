from functools import lru_cache
from importlib import import_module

from .base import LanguagePack


SUPPORTED_LANGUAGE_CODES = ("ja", "ko")


@lru_cache(maxsize=None)
def get_language(code: str) -> LanguagePack:
    """Load a language pack only when the installation enables it."""
    if code == "ja":
        return import_module("languages.japanese").JapaneseLanguagePack()
    if code == "ko":
        return import_module("languages.korean").KoreanLanguagePack()
    raise ValueError(f"不支援的來源語言：{code}")


def list_languages(codes: tuple[str, ...] | list[str] | None = None) -> list[LanguagePack]:
    selected = codes or SUPPORTED_LANGUAGE_CODES
    return [get_language(code) for code in selected]
