from dataclasses import dataclass


@dataclass(frozen=True)
class ParsedLine:
    id: int | None
    text: str
    is_blank: bool = False


@dataclass(frozen=True)
class LineResult:
    id: int | None
    original: str
    reading: str
    translation: str
    is_blank: bool = False
