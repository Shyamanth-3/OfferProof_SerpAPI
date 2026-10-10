import re

from .models import Extracted, Identifiers

UPI = re.compile(
    r"(?<![\w.\-@])[\w.\-]{2,}@(?:ok\w+|ybl|paytm|upi|axl|ibl|apl|sbi|icici|hdfcbank)(?![\w\-]|\.\w)",
    re.I,
)
EMAIL = re.compile(r"[\w.+\-]+@[\w\-]+(?:\.[\w\-]+)+")
PHONE = re.compile(r"(?<!\d)(?:\+?91[\s-]?)?([6-9]\d{4}[\s-]?\d{5})(?!\d)")
TG_LINK = re.compile(r"\bt\.me/(\w+)", re.I)
TG_AT = re.compile(r"telegram\W{0,40}@(\w{4,})|@(\w{4,})\W{0,40}telegram", re.I)
WA = re.compile(r"\b(?:wa\.me/\d+|chat\.whatsapp\.com/\w+)", re.I)
URL = re.compile(r"(?:https?://|www\.)[^\s<>\"')]+", re.I)

# words that are part of a company's legal/generic wording, not its identity
GENERIC = {
    "pvt", "ltd", "limited", "private", "inc", "llp", "the", "of", "and", "india",
    "technologies", "technology", "solutions", "services", "global", "systems", "group",
}

ROLE_WORDS = r"(?:Intern(?:ship)?|Developer|Engineer|Analyst|Executive|Associate|Trainee)"
ROLE = re.compile(rf"\b((?:[A-Z][\w+#/.\-]*\s+){{0,3}}{ROLE_WORDS}s?)\b")
NAME = r"([A-Z][\w&]*(?:\s+(?:[A-Z][\w&]*|Pvt\.?|Ltd\.?))*)"
# priority order; case-sensitive so "Work From Home" is not mistaken for "from <company>"
COMPANY_PATTERNS = [re.compile(p + r"\s+" + NAME) for p in ("Greetings from", "on behalf of", r"\bat", r"\bfrom")]
# "Wipro | Internship Program ..." on the first line (an email subject). Skips generic subject words.
SUBJECT = re.compile(r"^\s*(?:(?i:re|fwd?):\s*)?([A-Z][\w&.]*(?:\s+[A-Z&][\w&.]*){0,3})\s*\|\s*\S")
SUBJECT_STOP = {"congratulations", "offer", "urgent", "hiring", "job", "jobs", "internship", "important", "notice", "selected",
                "welcome", "apply", "openings", "opening", "registration", "invitation", "announcement", "alert", "update", "new"}
_NOT_A_COMPANY_LINE = re.compile(r"^\s*(to|dear|hi|hello)\b", re.I)


FREE_MAIL = {
    "gmail.com", "googlemail.com", "yahoo.com", "yahoo.in", "yahoo.co.in", "outlook.com", "hotmail.com",
    "live.com", "rediffmail.com", "protonmail.com", "proton.me", "icloud.com", "zohomail.com", "zoho.com",
}
_LIST_NEXT = re.compile(r"\s*[,&]")


def _brand_from_sender(text: str, sender_email) -> "str | None":
    """careers@examplelearn.example + 'Examplelearn' repeated in the body -> company 'Examplelearn'."""
    if not sender_email or "@" not in sender_email:
        return None
    dom = sender_email.split("@")[1]
    label = dom.split(".")[0]
    if dom in FREE_MAIL or len(label) < 4 or not label.isalnum():
        return None
    # the header line itself counts once, so require 3+ mentions
    return label.capitalize() if len(re.findall(rf"\b{re.escape(label)}\b", text, re.I)) >= 3 else None


def core_tokens(name: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9]+", name.lower()) if t not in GENERIC]


def _clean(xs) -> list[str]:
    return list(dict.fromkeys(xs))


def extract(text: str, company=None, sender_email=None, role=None) -> Extracted:
    upi = _clean(m.group(0).lower() for m in UPI.finditer(text))
    emails = _clean(m.group(0).lower() for m in EMAIL.finditer(text))
    phones = _clean(re.sub(r"\D", "", m.group(1)) for m in PHONE.finditer(text))
    tg = _clean([m.group(1) for m in TG_LINK.finditer(text)]
                + [m.group(1) or m.group(2) for m in TG_AT.finditer(text)])
    links = _clean(m.group(0).rstrip(".,;") for m in list(WA.finditer(text)) + list(URL.finditer(text))
                   + list(TG_LINK.finditer(text)))

    if not sender_email:
        skip = {m.group(0).lower() for ln in text.splitlines() if _NOT_A_COMPANY_LINE.match(ln) for m in EMAIL.finditer(ln)}
        sender_email = next((e for e in emails if e not in skip), None)
    if not company:
        first = next((l for l in text.splitlines() if l.strip()), "")
        m = SUBJECT.match(first)
        if m and m.group(1).lower() not in SUBJECT_STOP:
            company = m.group(1).strip().rstrip(".")
    if not company:
        for p in COMPANY_PATTERNS[:2]:  # "Greetings from X", "on behalf of X"
            m = p.search(text)
            if m:
                company = m.group(1).strip().rstrip(".")
                break
    if not company:
        company = _brand_from_sender(text, sender_email)
    if not company:
        for p in COMPANY_PATTERNS[2:]:  # bare "at X" / "from X": noisy, so skip list-like matches ("from MNCs, AWS & AICTE")
            m = p.search(text)
            if m and not _LIST_NEXT.match(text, m.end()):
                company = m.group(1).strip().rstrip(".")
                break
    if not role:
        m = ROLE.search(text)
        role = m.group(1).strip() if m else None

    return Extracted(
        company=company or None,
        sender_email=(sender_email or "").strip().lower() or None,
        role=role or None,
        identifiers=Identifiers(upi=upi, phones=phones, telegram=tg, emails=emails, links=links),
    )
