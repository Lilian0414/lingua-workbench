import os

from flask import Flask, jsonify, render_template, request

from core.errors import TranslationError
from core.formatter import build_results
from core.parser import non_blank_lines, parse_text
from languages import get_language, list_languages
from languages.registry import SUPPORTED_LANGUAGE_CODES
from providers import GoogleTransProvider, GroqProvider


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 64 * 1024

MAX_TEXT_LENGTH = 12_000
MAX_INSTRUCTION_LENGTH = 300

groq_provider = GroqProvider()
google_provider = GoogleTransProvider()


def _enabled_language_codes() -> tuple[str, ...]:
    requested = tuple(
        code.strip().lower()
        for code in os.getenv("ENABLED_LANGUAGES", "ja,ko").split(",")
        if code.strip()
    )
    enabled = tuple(code for code in requested if code in SUPPORTED_LANGUAGE_CODES)
    return enabled or SUPPORTED_LANGUAGE_CODES


ENABLED_LANGUAGE_CODES = _enabled_language_codes()
DEFAULT_SOURCE_LANGUAGE = os.getenv("DEFAULT_SOURCE_LANGUAGE", ENABLED_LANGUAGE_CODES[0])
if DEFAULT_SOURCE_LANGUAGE not in ENABLED_LANGUAGE_CODES:
    DEFAULT_SOURCE_LANGUAGE = ENABLED_LANGUAGE_CODES[0]


def _language(code: str):
    if code not in SUPPORTED_LANGUAGE_CODES:
        raise TranslationError(f"不支援的來源語言：{code}", status_code=400)
    if code not in ENABLED_LANGUAGE_CODES:
        raise TranslationError(f"這個部署沒有啟用來源語言：{code}", status_code=400)
    try:
        return get_language(code)
    except ValueError as exc:
        raise TranslationError(str(exc), status_code=400) from exc


def _render(error: str = "", status: int = 200, **context):
    source_code = context.get("source_language", DEFAULT_SOURCE_LANGUAGE)
    if source_code not in ENABLED_LANGUAGE_CODES:
        source_code = DEFAULT_SOURCE_LANGUAGE
        context["source_language"] = source_code
    context.setdefault("language", _language(source_code))
    context.setdefault("languages", list_languages(ENABLED_LANGUAGE_CODES))
    context.setdefault("source_language", source_code)
    context.setdefault("provider", "groq")
    context.setdefault("lyrics", "")
    context.setdefault("results", [])
    context.setdefault("error", error)
    return render_template("index.html", **context), status


@app.get("/")
def index():
    return _render()


@app.post("/")
def translate_document():
    lyrics = request.form.get("lyrics", "")
    source_language = request.form.get("source_language", DEFAULT_SOURCE_LANGUAGE)
    provider_name = request.form.get("provider", "groq")
    base = {
        "lyrics": lyrics,
        "source_language": source_language,
        "provider": provider_name,
    }
    try:
        language = _language(source_language)
        if len(lyrics) > MAX_TEXT_LENGTH:
            raise TranslationError("歌詞太長，請控制在 12,000 字以內。", status_code=400)
        lines = parse_text(lyrics)
        if not non_blank_lines(lines):
            raise TranslationError("請先貼上要翻譯的歌詞。", status_code=400)
        if provider_name == "groq":
            translations = groq_provider.translate(lines, language)
        elif provider_name == "google":
            translations = google_provider.translate(lines, language)
        else:
            raise TranslationError("不支援的翻譯服務。", status_code=400)
        return _render(
            **base,
            language=language,
            results=build_results(lines, translations, language),
        )
    except TranslationError as exc:
        return _render(exc.user_message, exc.status_code, **base)


def _api_payload():
    payload = request.get_json(silent=True) or {}
    source_language = str(payload.get("source_language", DEFAULT_SOURCE_LANGUAGE))
    language = _language(source_language)
    lyrics = str(payload.get("lyrics", ""))
    if not lyrics or len(lyrics) > MAX_TEXT_LENGTH:
        raise TranslationError("歌詞內容無效。", status_code=400)
    lines = parse_text(lyrics)
    try:
        target_id = int(payload.get("target_id"))
    except (TypeError, ValueError) as exc:
        raise TranslationError("句子編號無效。", status_code=400) from exc
    if not any(line.id == target_id for line in lines):
        raise TranslationError("找不到要翻譯的句子。", status_code=400)
    return payload, language, lines, target_id


@app.post("/api/regenerate-line")
def regenerate_line():
    try:
        payload, language, lines, target_id = _api_payload()
        instruction = str(payload.get("instruction", ""))[:MAX_INSTRUCTION_LENGTH]
        raw_current = payload.get("current_translations", {})
        current = {
            int(key): str(value)
            for key, value in raw_current.items()
            if str(key).isdigit()
        } if isinstance(raw_current, dict) else {}
        translation = groq_provider.regenerate_line(
            lines,
            target_id,
            language,
            current,
            instruction,
        )
        return jsonify({"translation": translation, "provider": groq_provider.name})
    except TranslationError as exc:
        response = jsonify({"error": exc.user_message})
        response.status_code = exc.status_code
        if exc.retry_after is not None:
            response.headers["Retry-After"] = str(exc.retry_after)
        return response


@app.post("/api/google-line")
def google_line():
    try:
        _, language, lines, target_id = _api_payload()
        target = next(line for line in lines if line.id == target_id)
        translation = google_provider.translate_line(target.text, language)
        return jsonify({"translation": translation, "provider": google_provider.name})
    except TranslationError as exc:
        return jsonify({"error": exc.user_message}), exc.status_code


@app.get("/health")
def health():
    return jsonify({"status": "ok", "languages": list(ENABLED_LANGUAGE_CODES)})


if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
