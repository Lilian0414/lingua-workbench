import json
import os
from typing import Any

from core.errors import TranslationError
from core.models import ParsedLine
from languages.base import LanguagePack


class GroqProvider:
    name = "Groq AI"

    def __init__(self, client: Any | None = None) -> None:
        self._client = client
        self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise TranslationError("尚未設定 GROQ_API_KEY。", status_code=503)
        from groq import Groq

        self._client = Groq(api_key=api_key, timeout=20.0, max_retries=0)
        return self._client

    @staticmethod
    def _schema(ids: list[int]) -> dict[str, Any]:
        properties = {str(line_id): {"type": "string"} for line_id in ids}
        return {
            "name": "lyrics_translation",
            "strict": True,
            "schema": {
                "type": "object",
                "properties": properties,
                "required": list(properties),
                "additionalProperties": False,
            },
        }

    @staticmethod
    def _source_payload(lines: list[ParsedLine]) -> dict[str, str]:
        return {str(line.id): line.text for line in lines if not line.is_blank and line.id is not None}

    def translate(self, lines: list[ParsedLine], language: LanguagePack) -> dict[int, str]:
        source = self._source_payload(lines)
        if not source:
            return {}
        preserved = {
            int(line_id): text for line_id, text in source.items() if language.should_preserve(text)
        }
        targets = {line_id: text for line_id, text in source.items() if int(line_id) not in preserved}
        if not targets:
            return preserved

        system = (
            f"你是專業的{language.display_name}歌詞譯者。把每一行翻成自然的台灣繁體中文，"
            "保留原本分行，不增刪、合併或拆分任何行。"
            f"{language.prompt_notes}只回傳符合 JSON Schema 的資料。"
        )
        user = "請依照行號逐行翻譯：\n" + json.dumps(targets, ensure_ascii=False)
        data = self._complete(system, user, [int(key) for key in targets])
        data.update(preserved)
        return data

    def regenerate_line(
        self,
        lines: list[ParsedLine],
        target_id: int,
        language: LanguagePack,
        current_translations: dict[int, str] | None = None,
        instruction: str = "",
    ) -> str:
        source = self._source_payload(lines)
        target_key = str(target_id)
        if target_key not in source:
            raise TranslationError("找不到要重新翻譯的句子。", status_code=400)
        if language.should_preserve(source[target_key]):
            return source[target_key]

        context = {
            "source_lines": source,
            "current_translations": {
                str(key): value for key, value in (current_translations or {}).items()
            },
            "target_id": target_id,
            "instruction": instruction.strip(),
        }
        system = (
            f"你是專業的{language.display_name}歌詞譯者。只重譯指定的一行為自然的台灣繁體中文，"
            "參考整首歌的上下文與現有譯文，並保持人稱、情緒與用詞一致。"
            f"{language.prompt_notes}只回傳符合 JSON Schema 的資料。"
        )
        data = self._complete(
            system,
            json.dumps(context, ensure_ascii=False),
            [target_id],
        )
        return data[target_id]

    def _complete(self, system: str, user: str, ids: list[int]) -> dict[int, str]:
        try:
            response = self._get_client().chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                response_format={"type": "json_schema", "json_schema": self._schema(ids)},
                temperature=0.35,
            )
            content = response.choices[0].message.content
            raw = json.loads(content)
            expected = {str(line_id) for line_id in ids}
            if set(raw) != expected or not all(isinstance(value, str) for value in raw.values()):
                raise ValueError("response does not contain every requested line")
            return {int(key): value.strip() for key, value in raw.items()}
        except TranslationError:
            raise
        except Exception as exc:
            status_code = getattr(exc, "status_code", None)
            response = getattr(exc, "response", None)
            if status_code is None and response is not None:
                status_code = getattr(response, "status_code", None)
            if status_code == 429:
                retry_after = None
                headers = getattr(response, "headers", {}) or {}
                try:
                    retry_after = int(headers.get("retry-after", ""))
                except (TypeError, ValueError):
                    pass
                raise TranslationError(
                    "翻譯服務目前太忙，請稍後再試。",
                    status_code=429,
                    retry_after=retry_after,
                ) from exc
            if status_code in {408, 504} or isinstance(exc, TimeoutError):
                raise TranslationError("翻譯逾時，請稍後重試。", status_code=504) from exc
            if isinstance(exc, (json.JSONDecodeError, ValueError, KeyError, IndexError)):
                raise TranslationError("翻譯回傳格式不完整，請再試一次。") from exc
            raise TranslationError("目前無法連線至翻譯服務，請稍後再試。", status_code=503) from exc
