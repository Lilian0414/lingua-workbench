from .models import ParsedLine


def parse_text(text: str) -> list[ParsedLine]:
    """Split text while preserving blank lines and stable non-blank IDs."""
    parsed: list[ParsedLine] = []
    next_id = 0
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            parsed.append(ParsedLine(id=None, text="", is_blank=True))
            continue
        parsed.append(ParsedLine(id=next_id, text=line))
        next_id += 1
    return parsed


def non_blank_lines(lines: list[ParsedLine]) -> list[ParsedLine]:
    return [line for line in lines if not line.is_blank]
