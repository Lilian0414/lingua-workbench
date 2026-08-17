from typing import Protocol


class LanguagePack(Protocol):
    code: str
    display_name: str
    native_name: str
    html_lang: str
    google_code: str
    reading_label: str
    prompt_notes: str

    def annotate(self, text: str) -> str: ...

    def should_preserve(self, text: str) -> bool: ...
