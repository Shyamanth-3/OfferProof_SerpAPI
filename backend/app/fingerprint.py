"""Pick 0-2 distinctive phrases from an offer to search as exact quotes. Pure: no network.

Fake offers are mass-produced templates, so the same wording shows up under different company
names. Everything specific to *this* recipient or company is stripped first; whatever remains is
what a template would share.
"""
import re

from .checks.text_red_flags import sentences
from .extract import EMAIL, PHONE, UPI, URL, TG_LINK, WA, core_tokens

MARK = " • "  # a removed span: words on either side were NOT adjacent in the original
MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)[a-z]*\.?"

STOP = frozenset(
    "a an and are as at be been but by can could did do does for from had has have he her his i if in into is it its "
    "may me my no not of on or our she should so such than that the their them then there these they this those to too "
    "us was we were what when where which who will with would you your yours please kindly also all any about after before".split()
)
# boilerplate genuine HR mail uses; matching it says nothing about origin
GENERIC = (
    "congratulations", "we are pleased to", "dear candidate", "thank you for applying", "best regards", "kind regards",
    "warm regards", "looking forward", "please find attached", "offer letter", "terms and conditions",
    "welcome to the team", "thank you for your interest", "we are delighted to", "pleased to inform",
    "do not hesitate", "feel free to contact",
)
RED = ("fee", "telegram", "whatsapp", "refundable", "registration", "interview", "guarantee")

_REMOVE = [  # order matters: dates and currency before bare numbers
    EMAIL, URL, TG_LINK, WA, UPI, PHONE,
    re.compile(r"\b[\w-]+(?:\.[\w-]+)*\.(?:com|in|org|net|io|me|gle|ly|co)\b/?\S*", re.I),  # forms.gle/xyz
    re.compile(rf"\b{MONTH}\s+\d{{1,2}}(?:st|nd|rd|th)?(?:,?\s+\d{{2,4}})?", re.I),
    re.compile(rf"\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH}(?:,?\s+\d{{2,4}})?", re.I),
    re.compile(r"\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.I),
    re.compile(r"(?:₹|\brs\b\.?|\binr\b)\s*[\d,]+(?:\.\d+)?", re.I),
    re.compile(r"\b\d[\d,./:%\-]*"),
]
_GREETING = re.compile(r"\b((?i:dear|mr|ms|mrs|hi|hello))\b\.?\s+[A-Z][\w'’-]*(?:\s+[A-Z][\w'’-]*)?")


def _segments(sentence: str, extracted) -> list[list[str]]:
    """Cleaned sentence as runs of adjacent words, split wherever something was removed."""
    s = _GREETING.sub(rf"\1{MARK}", sentence)
    names = []
    if getattr(extracted, "company", None):
        names += [extracted.company] + [t for t in core_tokens(extracted.company) if len(t) >= 4]
    sender = getattr(extracted, "sender_email", None)
    if sender and "@" in sender:
        label = sender.split("@")[1].split(".")[0]
        if len(label) >= 4:
            names.append(label)
    for n in sorted(set(names), key=len, reverse=True):
        s = re.sub(re.escape(n), MARK, s, flags=re.I)
    for pat in _REMOVE:
        s = pat.sub(MARK, s)
    s = re.sub(r"[^\w\s'’\-•]", " ", s).replace("_", " ")
    return [seg.split() for seg in s.split("•") if seg.split()]


def _score(words: list[str]) -> int:
    return sum(1 for w in words if w.lower() not in STOP and len(w) >= 5) + 2 * sum(
        any(k in w.lower() for k in RED) for w in words
    )


def _best_window(segments: list[list[str]]) -> list[str] | None:
    best, best_key = None, None
    for seg in segments:
        for i in range(len(seg) - 7):
            for n in range(8, min(12, len(seg) - i) + 1):
                w = seg[i : i + n]
                key = (_score(w), -n)  # highest score; on a tie prefer the shorter phrase
                if best_key is None or key > best_key:
                    best, best_key = w, key
    return best


def _tokens(words: list[str]) -> set[str]:
    return {w.lower() for w in words}


def select_phrases(redacted_text: str, extracted) -> list[str]:
    cands = []
    for idx, sent in enumerate(sentences(redacted_text)):
        segs = _segments(sent, extracted)
        words = [w for seg in segs for w in seg]
        if len(words) < 8:
            continue
        low = " ".join(words).lower()
        if any(g in low for g in GENERIC):
            continue
        if sum(w.lower() in STOP for w in words) / len(words) > 0.5:
            continue
        win = _best_window(segs)
        if win:
            cands.append((-_score(words), idx, win))
    cands.sort(key=lambda c: (c[0], c[1]))  # best score first, earlier sentence on a tie
    out: list[list[str]] = []
    for _, _, win in cands[:2]:
        if out:
            a, b = _tokens(out[0]), _tokens(win)
            if len(a & b) / min(len(a), len(b)) > 0.5:
                break  # second phrase mostly repeats the first: drop it
        out.append(win)
    return [" ".join(w) for w in out]
