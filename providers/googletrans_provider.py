import asyncio
from typing import Any

from core.errors import TranslationError
from core.models import ParsedLine
from languages.base import LanguagePack


class GoogleTransProvider:
    name = "Google 翻譯"

    def __init__(self, translator: Any | None = None) -> None:
        self._translator = translator

    def _get_translator(self) -> Any:
        if self._translator is None:
            from googletrans import Translator

            self._translator = Translator()
        return self._translator

    @staticmethod
    def _run(value: Any) -> Any:
        if hasattr(value, "__await__"):
            return asyncio.run(value)
        return value

    def translate(self, lines: list[ParsedLine], language: LanguagePack) -> dict[int, str]:
        targets = [line for line in lines if not line.is_blank and line.id is not None]
        if not targets:
            return {}
        try:
            result = self._run(
                self._get_translator().translate(
                    [line.text for line in targets],
                    src=language.google_code,
                    dest="zh-tw",
                )
            )
            if not isinstance(result, list):
                result = [result]
            if len(result) != len(targets):
                raise ValueError("translation count mismatch")
            return {line.id: item.text.strip() for line, item in zip(targets, result, strict=True)}
        except Exception as exc:
            raise TranslationError("Google 翻譯暫時無法使用，請稍後再試。", status_code=503) from exc

    def translate_line(self, text: str, language: LanguagePack) -> str:
        if not text.strip():
            return ""
        try:
            result = self._run(
                self._get_translator().translate(
                    text,
                    src=language.google_code,
                    dest="zh-tw",
                )
            )
            return result.text.strip()
        except Exception as exc:
            raise TranslationError("Google 翻譯暫時無法使用，請稍後再試。", status_code=503) from exc
