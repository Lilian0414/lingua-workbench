import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from core.errors import TranslationError
from core.models import ParsedLine
from languages.base import LanguagePack


class GoogleTransProvider:
    name = "Google 翻譯"

    def __init__(
        self,
        translator: Any | None = None,
        *,
        translator_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._translator = translator
        self._translator_factory = translator_factory

    def _new_translator(self) -> Any:
        if self._translator is not None:
            return self._translator
        if self._translator_factory is not None:
            return self._translator_factory()
        from googletrans import Translator

        return Translator()

    def _translate_once(self, text: str | list[str], *, src: str, dest: str) -> Any:
        translator = self._new_translator()

        async def execute() -> Any:
            if hasattr(translator, "__aenter__") and hasattr(translator, "__aexit__"):
                async with translator as active_translator:
                    result = active_translator.translate(text, src=src, dest=dest)
                    return await result if inspect.isawaitable(result) else result
            result = translator.translate(text, src=src, dest=dest)
            return await result if inspect.isawaitable(result) else result

        return asyncio.run(execute())

    def translate(self, lines: list[ParsedLine], language: LanguagePack) -> dict[int, str]:
        targets = [line for line in lines if not line.is_blank and line.id is not None]
        if not targets:
            return {}
        try:
            result = self._translate_once(
                [line.text for line in targets],
                src=language.google_code,
                dest="zh-tw",
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
            result = self._translate_once(
                text,
                src=language.google_code,
                dest="zh-tw",
            )
            return result.text.strip()
        except Exception as exc:
            raise TranslationError("Google 翻譯暫時無法使用，請稍後再試。", status_code=503) from exc
