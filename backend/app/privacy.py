import re

# Not preceded by + or / so "+91…" and "wa.me/91…" are phone numbers, not Aadhaar.
AADHAAR = re.compile(r"(?<![\d+/])\b\d{4}\s?\d{4}\s?\d{4}\b(?!\d)")
PAN = re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b")
# Unspaced 12 digits that look like 91 + Indian mobile are far likelier a phone than an Aadhaar.
_PHONE_91 = re.compile(r"91[6-9]\d{9}")


def _aadhaar_sub(m: re.Match) -> str:
    return m.group(0) if _PHONE_91.fullmatch(m.group(0)) else "[REDACTED]"


def redact(text: str) -> tuple[str, list[str]]:
    found = []
    out = AADHAAR.sub(_aadhaar_sub, text)
    if out != text:
        found.append("aadhaar")
    out2 = PAN.sub("[REDACTED]", out)
    if out2 != out:
        found.append("pan")
    return out2, found
