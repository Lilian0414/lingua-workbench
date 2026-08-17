import json
import os
from typing import Any

import httpx

from core.errors import TranslationError
from core.models import ParsedLine
from languages.base import LanguagePack


class LLMProvider:
    """Translate through any OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        client: Any | None = None,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        display_name: str | None = None,
        response_format: str | None = None,
    ) -> None:
        self._client = client
        self.api_key = api_key or os.getenv("LLM_API_KEY") or os.getenv("GROQ_API_KEY")
        self.base_url = (
            base_url
            or os.getenv("LLM_BASE_URL")
            or "https://api.groq.com/openai/v1"
        ).rstrip("/")
        self.model = (
            model
            or os.getenv("LLM_MODEL")
            or os.getenv("GROQ_MODEL")
            or "openai/gpt-oss-20b"
        )
        self.name = display_name or os.getenv("LLM_DISPLAY_NAME", "AI 模型")
        configured_format = response_format or os.getenv("LLM_RESPONSE_FORMAT", "json_schema")
        self.response_format = (
            configured_format
            if configured_format in {"json_schema", "json_object", "prompt_only"}
            else "json_schema"
        )

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
            f"{language.prompt_notes}只回傳以行號為 key、譯文為 value 的 JSON object。"
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
            f"{language.prompt_notes}只回傳以指定行號為 key 的 JSON object。"
        )
        data = self._complete(system, json.dumps(context, ensure_ascii=False), [target_id])
        return data[target_id]

    def _response_format_payload(self, ids: list[int]) -> dict[str, Any] | None:
        if self.response_format == "json_schema":
            return {"type": "json_schema", "json_schema": self._schema(ids)}
        if self.response_format == "json_object":
            return {"type": "json_object"}
        return None

    def _post(self, payload: dict[str, Any]) -> Any:
        if not self.api_key:
            raise TranslationError(
                "此部署尚未設定 LLM_API_KEY。請由網站維護者設定 AI 翻譯服務。",
                status_code=503,
            )
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        url = f"{self.base_url}/chat/completions"
        if self._client is not None:
            return self._client.post(url, headers=headers, json=payload, timeout=20.0)
        return httpx.post(url, headers=headers, json=payload, timeout=20.0)

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        cleaned = content.strip()
        if cleaned.startswith("```") and cleaned.endswith("```"):
            cleaned = cleaned[3:-3].strip()
            if cleaned.lower().startswith("json"):
                cleaned = cleaned[4:].strip()
        return cleaned

    def _complete(self, system: str, user: str, ids: list[int]) -> dict[int, str]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.35,
        }
        response_format = self._response_format_payload(ids)
        if response_format is not None:
            payload["response_format"] = response_format

        try:
            response = self._post(payload)
            status_code = int(getattr(response, "status_code", 200))
            if status_code == 429:
                retry_after = None
                try:
                    retry_after = int(response.headers.get("retry-after", ""))
                except (TypeError, ValueError):
                    pass
                raise TranslationError(
                    "AI 翻譯服務目前太忙，請稍後再試。",
                    status_code=429,
                    retry_after=retry_after,
                )
            if status_code in {408, 504}:
                raise TranslationError("AI 翻譯逾時，請稍後重試。", status_code=504)
            if status_code >= 400:
                raise TranslationError(
                    "AI 翻譯服務拒絕了請求，請檢查模型、端點與回傳格式設定。",
                    status_code=502,
                )

            body = response.json()
            content = body["choices"][0]["message"]["content"]
            raw = json.loads(self._strip_code_fence(content))
            expected = {str(line_id) for line_id in ids}
            if set(raw) != expected or not all(isinstance(value, str) for value in raw.values()):
                raise ValueError("response does not contain every requested line")
            return {int(key): value.strip() for key, value in raw.items()}
        except TranslationError:
            raise
        except httpx.TimeoutException as exc:
            raise TranslationError("AI 翻譯逾時，請稍後重試。", status_code=504) from exc
        except httpx.RequestError as exc:
            raise TranslationError("目前無法連線至 AI 翻譯服務，請稍後再試。", status_code=503) from exc
        except (json.JSONDecodeError, ValueError, KeyError, IndexError, TypeError) as exc:
            raise TranslationError("AI 翻譯回傳格式不完整，請再試一次。") from exc
