import json
from types import SimpleNamespace

import pytest

from core.errors import TranslationError
from core.parser import parse_text
from languages import get_language
from providers.googletrans_provider import GoogleTransProvider
from providers.llm_provider import LLMProvider


class FakeResponse:
    def __init__(self, content, status_code=200, headers=None):
        self.content = content
        self.status_code = status_code
        self.headers = headers or {}

    def json(self):
        return {"choices": [{"message": {"content": self.content}}]}


class FakeClient:
    def __init__(self, content):
        self.response = FakeResponse(content)
        self.calls = []

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


def fake_provider(content, **kwargs):
    client = FakeClient(content)
    provider = LLMProvider(
        client,
        api_key="test-key",
        base_url="https://llm.example/v1",
        model="example-model",
        **kwargs,
    )
    return provider, client


def test_llm_uses_selected_language_and_strict_ids():
    provider, client = fake_provider('{"0":"你好","1":"世界"}')
    result = provider.translate(parse_text("안녕\n세계"), get_language("ko"))
    assert result == {0: "你好", 1: "世界"}
    url, request = client.calls[0]
    assert url == "https://llm.example/v1/chat/completions"
    assert request["headers"]["Authorization"] == "Bearer test-key"
    assert request["json"]["model"] == "example-model"
    assert "韓文" in request["json"]["messages"][0]["content"]
    schema = request["json"]["response_format"]["json_schema"]["schema"]
    assert schema["required"] == ["0", "1"]
    assert schema["additionalProperties"] is False


def test_llm_rejects_missing_line():
    provider, _ = fake_provider('{"0":"只有一行"}')
    with pytest.raises(TranslationError, match="格式不完整"):
        provider.translate(parse_text("一\n二"), get_language("ja"))


def test_llm_regeneration_uses_context_and_instruction():
    provider, client = fake_provider('{"1":"換個說法"}')
    value = provider.regenerate_line(
        parse_text("一\n二"), 1, get_language("ja"), {0: "壹", 1: "貳"}, "更口語"
    )
    assert value == "換個說法"
    payload = json.loads(client.calls[0][1]["json"]["messages"][1]["content"])
    assert payload["target_id"] == 1
    assert payload["instruction"] == "更口語"


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        ("json_object", {"type": "json_object"}),
        ("prompt_only", None),
    ],
)
def test_llm_supports_provider_specific_response_formats(mode, expected):
    provider, client = fake_provider('{"0":"翻譯"}', response_format=mode)
    provider.translate(parse_text("原文"), get_language("ja"))
    payload = client.calls[0][1]["json"]
    assert payload.get("response_format") == expected


def test_llm_accepts_markdown_wrapped_json():
    provider, _ = fake_provider('```json\n{"0":"翻譯"}\n```', response_format="prompt_only")
    assert provider.translate(parse_text("原文"), get_language("ja")) == {0: "翻譯"}


def test_llm_requires_deployment_key(monkeypatch):
    for name in ("LLM_API_KEY", "GROQ_API_KEY"):
        monkeypatch.delenv(name, raising=False)
    provider = LLMProvider(FakeClient('{"0":"翻譯"}'), api_key=None)
    with pytest.raises(TranslationError, match="LLM_API_KEY"):
        provider.translate(parse_text("原文"), get_language("ja"))


class FakeGoogle:
    def __init__(self):
        self.calls = []

    def translate(self, text, **kwargs):
        self.calls.append((text, kwargs))
        if isinstance(text, list):
            return [SimpleNamespace(text=f"譯:{item}") for item in text]
        return SimpleNamespace(text=f"譯:{text}")


@pytest.mark.parametrize(("code", "google_code"), [("ja", "ja"), ("ko", "ko")])
def test_google_provider_uses_language_source_code(code, google_code):
    translator = FakeGoogle()
    result = GoogleTransProvider(translator).translate(parse_text("第一行"), get_language(code))
    assert result == {0: "譯:第一行"}
    assert translator.calls[0][1] == {"src": google_code, "dest": "zh-tw"}


def test_google_provider_creates_fresh_async_translator_for_consecutive_calls():
    instances = []

    class LoopBoundTranslator:
        def __init__(self):
            self.closed = False
            instances.append(self)

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_value, traceback):
            self.closed = True

        async def translate(self, text, **kwargs):
            assert not self.closed
            return SimpleNamespace(text=f"譯:{text}")

    provider = GoogleTransProvider(translator_factory=LoopBoundTranslator)
    language = get_language("ja")

    assert provider.translate_line("君が好き", language) == "譯:君が好き"
    assert provider.translate_line("月が綺麗", language) == "譯:月が綺麗"
    assert len(instances) == 2
    assert all(instance.closed for instance in instances)
