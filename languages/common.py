import re


_CHANT_RE = re.compile(
    r"^[\s♪♫♬・･~〜ー\-—…!?！？()（）]*(?:"
    r"la|na|oh|ah|woo|wow|yeah|hey|ha|lalala|nanana|啦|喔|啊"
    r")[\s♪♫♬・･~〜ー\-—…!?！？()（）a-zA-Zぁ-んァ-ン가-힣]*$",
    re.IGNORECASE,
)


def looks_like_chant(text: str) -> bool:
    compact = text.strip()
    return bool(compact and _CHANT_RE.fullmatch(compact))
