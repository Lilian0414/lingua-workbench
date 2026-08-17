from core.formatter import build_results
from core.parser import non_blank_lines, parse_text


class FakeLanguage:
    def annotate(self, text):
        return f"reading:{text}"


def test_parser_preserves_blank_lines_and_stable_ids():
    lines = parse_text("一行\n\n二行\r\n三行")
    assert [(line.id, line.text, line.is_blank) for line in lines] == [
        (0, "一行", False),
        (None, "", True),
        (1, "二行", False),
        (2, "三行", False),
    ]


def test_non_blank_lines_filters_only_layout_rows():
    assert [line.text for line in non_blank_lines(parse_text("a\n\nb"))] == ["a", "b"]


def test_formatter_keeps_alignment_and_adds_reading():
    results = build_results(parse_text("a\n\nb"), {0: "甲", 1: "乙"}, FakeLanguage())
    assert results[0].reading == "reading:a"
    assert results[1].is_blank is True
    assert results[2].translation == "乙"
