import pytest

from languages import get_language, list_languages
from languages.japanese import JapaneseLanguagePack
from languages.korean import KoreanLanguagePack


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("123", "hyaku nijuu san"),
        ("3.14", "san ten ichi yon"),
        ("００７", "zero zero nana"),
        ("3月9日", "sangatsu kokonoka"),
        ("1人と20歳", "hitori to hatachi"),
        ("4時10分", "yoji juppun"),
    ],
)
def test_japanese_number_readings(source, expected):
    assert JapaneseLanguagePack().annotate(source) == expected


def test_japanese_pack_uses_hepburn():
    reading = JapaneseLanguagePack().annotate("私が好き")
    assert "watashi" in reading.lower()
    assert "suki" in reading.lower()


def test_korean_pack_passes_pronunciation_options():
    calls = []

    def fake(text, **options):
        calls.append((text, options))
        return "annyeonghaseyo"

    pack = KoreanLanguagePack(fake)
    assert pack.annotate("안녕하세요") == "annyeonghaseyo"
    assert calls[0][1] == {"use_pronunciation_rules": True, "casing_option": "lowercase"}


def test_korean_pack_falls_back_for_simple_callable():
    pack = KoreanLanguagePack(lambda text: "hangeul")
    assert pack.annotate("한글") == "hangeul"


def test_registry_exposes_only_mvp_languages():
    assert [pack.code for pack in list_languages()] == ["ja", "ko"]
    assert get_language("ko").google_code == "ko"
    with pytest.raises(ValueError):
        get_language("fr")


@pytest.mark.parametrize("code", ["ja", "ko"])
def test_language_packs_preserve_common_chants(code):
    assert get_language(code).should_preserve("la la la") is True
