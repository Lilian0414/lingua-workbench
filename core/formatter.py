from languages.base import LanguagePack

from .models import LineResult, ParsedLine


def build_results(
    lines: list[ParsedLine],
    translations: dict[int, str],
    language: LanguagePack,
) -> list[LineResult]:
    results: list[LineResult] = []
    for line in lines:
        if line.is_blank:
            results.append(LineResult(None, "", "", "", is_blank=True))
            continue
        assert line.id is not None
        results.append(
            LineResult(
                id=line.id,
                original=line.text,
                reading=language.annotate(line.text),
                translation=translations.get(line.id, ""),
            )
        )
    return results
