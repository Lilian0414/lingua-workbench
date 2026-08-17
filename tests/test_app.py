from types import SimpleNamespace

import pytest

import app as application


@pytest.fixture()
def client():
    application.app.config.update(TESTING=True)
    return application.app.test_client()


def test_health_lists_languages(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "languages": ["ja", "ko"]}


def test_home_has_both_language_choices(client):
    response = client.get("/")
    assert response.status_code == 200
    assert 'value="ja"' in response.text
    assert 'value="ko"' in response.text
    assert "日韓歌詞手帖" in response.text
    assert 'class="translation-sheet"' in response.text
    assert 'class="provider-option"' in response.text


def test_korean_document_translation_renders_reading(client, monkeypatch):
    monkeypatch.setattr(application.google_provider, "translate", lambda lines, language: {0: "你好"})
    monkeypatch.setattr(application.get_language("ko"), "annotate", lambda text: "annyeong", raising=False)
    response = client.post("/", data={
        "lyrics": "안녕",
        "source_language": "ko",
        "provider": "google",
    })
    assert response.status_code == 200
    assert "annyeong" in response.text
    assert "你好" in response.text
    assert 'data-language="ko"' in response.text
    assert 'class="lyric-line"' in response.text
    assert 'class="style-select"' in response.text
    assert 'class="line-button reset-line-button"' in response.text


def test_invalid_language_returns_400(client):
    response = client.post("/", data={"lyrics": "bonjour", "source_language": "fr", "provider": "google"})
    assert response.status_code == 400
    assert "不支援的來源語言" in response.text


def test_empty_text_returns_400(client):
    response = client.post("/", data={"lyrics": "   ", "source_language": "ja", "provider": "ai"})
    assert response.status_code == 400


def test_google_line_api_keeps_selected_language(client, monkeypatch):
    captured = {}

    def translate_line(text, language):
        captured.update(text=text, code=language.code)
        return "候選"

    monkeypatch.setattr(application.google_provider, "translate_line", translate_line)
    response = client.post("/api/google-line", json={
        "lyrics": "안녕",
        "source_language": "ko",
        "target_id": 0,
    })
    assert response.status_code == 200
    assert response.get_json()["translation"] == "候選"
    assert captured == {"text": "안녕", "code": "ko"}


def test_google_line_api_succeeds_twice_with_fresh_async_clients(client, monkeypatch):
    instances = []

    class AsyncTranslator:
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

    monkeypatch.setattr(
        application,
        "google_provider",
        application.GoogleTransProvider(translator_factory=AsyncTranslator),
    )
    payload = {"lyrics": "君が好き", "source_language": "ja", "target_id": 0}

    first = client.post("/api/google-line", json=payload)
    second = client.post("/api/google-line", json=payload)

    assert first.status_code == second.status_code == 200
    assert first.get_json()["translation"] == second.get_json()["translation"] == "譯:君が好き"
    assert len(instances) == 2
    assert all(instance.closed for instance in instances)


def test_regenerate_api_passes_context(client, monkeypatch):
    captured = {}

    def regenerate(lines, target_id, language, current, instruction):
        captured.update(target_id=target_id, code=language.code, current=current, instruction=instruction)
        return "新譯文"

    monkeypatch.setattr(application.llm_provider, "regenerate_line", regenerate)
    response = client.post("/api/regenerate-line", json={
        "lyrics": "君が好き",
        "source_language": "ja",
        "target_id": 0,
        "current_translations": {"0": "喜歡你"},
        "instruction": "更有詩意",
    })
    assert response.status_code == 200
    assert response.get_json()["translation"] == "新譯文"
    assert captured == {
        "target_id": 0,
        "code": "ja",
        "current": {0: "喜歡你"},
        "instruction": "更有詩意",
    }
