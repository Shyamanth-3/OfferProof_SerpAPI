"""No API: regex red flags with clause-bounded negation."""
import re

from ..extract import UPI
from . import result

ID, TITLE, WEIGHT, ENGINE = "text_red_flags", "Message red flags", 30, None

_AMT = r"(?:rs\.?|₹|inr)"
PATTERNS = {
    "FEE": [
        r"(?:registration|training|security|processing|onboarding|kit|verification|joining|refundable|interview)\s+(?:fee|fees|charge|charges|amount|deposit)\b",
        rf"\bpay\s+{_AMT}\s*\d",
        rf"\bdeposit\s+{_AMT}?\s*\d",
        r"\b(?:fees?|paise|amount)\s+(?:bharna|jama|dena|pay\s+karna)\b",
        r"\bjama\s+karo\b",
        UPI.pattern,
    ],
    "OFF_PLATFORM": [
        r"\bt\.me/",
        r"\bwa\.me/",
        r"\bchat\.whatsapp\.com",
        r"\bcontact\s+(?:hr|us)\s+on\s+(?:telegram|whatsapp)",
        r"\binterview\s+(?:on|via|through)\s+(?:telegram|whatsapp)",
    ],
    "NO_INTERVIEW": [r"\bwithout\s+(?:any\s+)?interview", r"\bdirect\s+selection", r"\bno\s+interview\s+required"],
    "URGENCY": [r"\bwithin\s+24\s+hours", r"\blimited\s+seats", r"\blast\s+date\s+(?:is\s+)?today", r"\bimmediately\s+or\b"],
    "UNREALISTIC_PAY": [rf"\bearn\s+{_AMT}\s*\d[\d,]*\s*(?:per|a|/)\s*day"],
    # soft: fees mentioned but never stated, typical of paid "training" programs
    "FEES_UNSTATED": [r"\bapplicable\s+(?:program(?:me)?\s+)?fees?\b", r"\bfees?\s+(?:details|structure)\b"],
    # no genuine employer can promise you a job; "guaranteed placement" is how paid courses sell
    "JOB_GUARANTEE": [
        r"\b(?:100\s*%|guaranteed|assured)\s+(?:job|placement|employment)s?\b",
        r"\b(?:job|placement)\s+guarantee\b",
    ],
    # applying through a free form or shortened link instead of the company's own site
    "APPLY_VIA_FORM": [
        r"\b(?:forms\.gle|docs\.google\.com/forms|forms\.office\.com|forms\.microsoft\.com|typeform\.com|jotform\.com|tally\.so)/",
        r"\b(?:bit\.ly|tinyurl\.com|cutt\.ly|rb\.gy|is\.gd|t\.ly)/",
    ],
    # soft: wording of a course being sold rather than a job being offered
    "COURSE_SELLING": [r"\benrol(?:l|lment)\s+now\b", r"\bcourse\s+completion\b"],
    "TASK_SCAM": [
        r"\blike\s+(?:and|&)\s+(?:subscribe|rate)",
        r"\brate\s+(?:hotels|products|videos)",
        r"\bprepaid\s+task",
        r"\btelegram\s+task",
    ],
}
# TRAINING_FIRST needs both: a training phase AND a stipend that only comes later or "subject to" something
TRAINING = re.compile(r"\b(?:training\s+(?:phase|period)|industry\s+training|successfully\s+complete\s+the\s+training)", re.I)
STIPEND_LATER = re.compile(r"\b(?:performance[- ]based\s+stipend|stipend[- ]based\s+internship|eligible\s+for\s+(?:a\s+)?(?:performance[- ]based\s+)?stipend)", re.I)
SOFT = {"FEES_UNSTATED", "TRAINING_FIRST", "COURSE_SELLING"}  # never escalate a message to "fail" by themselves
_COMPILED = {k: [re.compile(p, re.I) for p in ps] for k, ps in PATTERNS.items()}
_NEGATOR = re.compile(
    r"\b(?:never|no|not|don't|do\s+not|won't|will\s+not|doesn't|does\s+not|without|zero|nahi|nahin|mat)\b|free\s+of\s+cost",
    re.I,
)
_CLAUSE_END = re.compile(r"[,;:!?\n]|\.(?=\s)")
_STIPEND = re.compile(rf"{_AMT}\s*([\d,]+)\s*(?:/|per|a)\s*month", re.I)


PLAIN = {
    "FEE": "a fee is demanded",
    "OFF_PLATFORM": "pushes you to Telegram/WhatsApp",
    "NO_INTERVIEW": "no interview",
    "URGENCY": "pressure to act fast",
    "UNREALISTIC_PAY": "unrealistic pay",
    "TASK_SCAM": "task-scam wording",
    "JOB_GUARANTEE": "guarantees a job",
    "APPLY_VIA_FORM": "applying goes through a generic form or shortened link, not the company's own site",
    "FEES_UNSTATED": "fees mentioned but never stated",
    "TRAINING_FIRST": "training comes before any pay",
    "COURSE_SELLING": "reads like a course being sold",
}


def _norm(text: str) -> str:
    text = text.replace("’", "'")
    return re.sub(r"\b(rs|inr)\.\s*", r"\1 ", text, flags=re.I)  # "Rs. 500" -> "Rs 500", so the dot isn't a clause end


def _negated(text: str, start: int) -> bool:
    clause_start = max((m.end() for m in _CLAUSE_END.finditer(text, 0, start)), default=0)
    words = text[clause_start:start].split()[-6:]  # negator must sit within 6 words before the match
    return bool(_NEGATOR.search(" ".join(words)))


def detect(text: str) -> dict[str, list[str]]:
    text = _norm(text)
    flags: dict[str, list[str]] = {}
    for flag, pats in _COMPILED.items():
        for p in pats:
            for m in p.finditer(text):
                if not _negated(text, m.start()):
                    flags.setdefault(flag, []).append(m.group(0).strip())
    t, st = TRAINING.search(text), STIPEND_LATER.search(text)
    if t and st and not _negated(text, st.start()):
        flags["TRAINING_FIRST"] = [f"{t.group(0)} … {st.group(0)}"]
    if re.search(r"intern", text, re.I):
        for m in _STIPEND.finditer(text):
            if int(m.group(1).replace(",", "") or 0) > 80_000 and not _negated(text, m.start()):
                flags.setdefault("UNREALISTIC_PAY", []).append(m.group(0).strip())
    return flags


def run(ctx, serp=None):
    flags = detect(ctx.text)
    names = list(flags)
    quotes = "; ".join(f'"{flags[f][0]}"' for f in names)
    hard = [n for n in names if n not in SOFT and n != "FEE"]
    if "FEE" in flags or len(hard) >= 2:
        status = "fail"
    elif names:  # one hard flag, or any soft flags: warn
        status = "warn"
    else:
        status = "pass"
    said = "; ".join(f"{PLAIN.get(n, n)} (“{flags[n][0]}”)" for n in names)
    finding = f"Red flags in the message: {said}." if names else "No fee demand, off-platform push, form-link application or pressure tactics found in the text."
    return result(ID, TITLE, WEIGHT, status, finding, flags=names)
