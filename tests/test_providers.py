import json
from types import SimpleNamespace

import pytest

from core.errors import TranslationError
from core.parser import parse_text
from languages import get_language
from providers.googletrans_provider import GoogleTransProvider
from providers.groq_provider import GroqProvider


class FakeCompletions:
    def __init__(self, content):
        self.content = content
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content))]
        )


def fake_client(content):
    completions = FakeCompletions(content)
    client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return client, completions


def test_groq_uses_selected_language_and_strict_ids():
    client, completions = fake_client('{"0":"你好","1":"世界"}')
    result = GroqProvider(client).translate(parse_text("안녕\n세계"), get_language("ko"))
    assert result == {0: "你好", 1: "世界"}
    assert "韓文" in completions.kwargs["messages"][0]["content"]
    schema = completions.kwargs["response_format"]["json_schema"]["schema"]
    assert schema["required"] == ["0", "1"]
    assert schema["additionalProperties"] is False


def test_groq_rejects_missing_line():
    client, _ = fake_client('{"0":"只有一行"}')
    with pytest.raises(TranslationError, match="格式不完整"):
        GroqProvider(client).translate(parse_text("一\n二"), get_language("ja"))


def test_groq_regeneration_uses_context_and_instruction():
    client, completions = fake_client('{"1":"換個說法"}')
    value = GroqProvider(client).regenerate_line(
        parse_text("一\n二"), 1, get_language("ja"), {0: "壹", 1: "貳"}, "更口語"
    )
    assert value == "換個說法"
    payload = json.loads(completions.kwargs["messages"][1]["content"])
    assert payload["target_id"] == 1
    assert payload["instruction"] == "更口語"


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
