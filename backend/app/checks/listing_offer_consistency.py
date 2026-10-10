"""Does the offer match the listing the student applied to? Compares fields extracted from both texts. No search."""
import re

from ..extract import core_tokens, extract
from . import result
from .job_listing import _stems

ID, TITLE, WEIGHT, ENGINE = "listing_offer_consistency", "Listing vs offer", 15, None

CITIES = {
    "bengaluru": "Bengaluru", "bangalore": "Bengaluru", "mumbai": "Mumbai", "new delhi": "Delhi", "delhi": "Delhi",
    "gurgaon": "Gurugram", "gurugram": "Gurugram", "noida": "Noida", "hyderabad": "Hyderabad", "chennai": "Chennai",
    "pune": "Pune", "kolkata": "Kolkata", "ahmedabad": "Ahmedabad", "jaipur": "Jaipur", "kochi": "Kochi",
    "coimbatore": "Coimbatore", "indore": "Indore", "chandigarh": "Chandigarh", "remote": "Remote",
    "work from home": "Remote", "wfh": "Remote",
}
_CITY = re.compile(r"\b(" + "|".join(sorted(map(re.escape, CITIES), key=len, reverse=True)) + r")\b", re.I)
_AMOUNT = re.compile(
    r"(?:(?:₹|\brs\b\.?|\binr\b)\s*(?P<a>[\d,]+(?:\.\d+)?)\s*(?P<au>lpa|lakhs?|k)?|(?P<b>\d[\d,.]*)\s*(?P<bu>lpa|k)\b)", re.I)
_PAY_WORDS = re.compile(r"stipend|salary|ctc|package|compensation|\bpay\b|per month|/\s*month|lpa|per annum|a year|per year", re.I)
_NOT_PAY = re.compile(r"fee|deposit|registration|refund", re.I)
_YEARLY = re.compile(r"per annum|/\s*year|a year|per year|\bp\.?a\b", re.I)


def _sentence(text: str, start: int, end: int) -> str:
    lo = max(text.rfind(". ", 0, start) + 1, text.rfind("\n", 0, start) + 1, 0)
    stops = [i for i in (text.find(". ", end), text.find("\n", end)) if i != -1]
    return text[lo: min(stops) if stops else len(text)]


def extract_pay(text: str):
    """First pay-looking amount as (monthly rupees, text as written), or None. Fees and deposits are skipped."""
    text = re.sub(r"\b(rs|inr)\.\s*", r"Rs ", text, flags=re.I)  # "Rs. 500" would otherwise look like a sentence end
    for m in _AMOUNT.finditer(text):
        sent = _sentence(text, m.start(), m.end())
        if not _PAY_WORDS.search(sent) or _NOT_PAY.search(sent):
            continue
        value = float((m.group("a") or m.group("b")).replace(",", "").rstrip("."))
        unit = (m.group("au") or m.group("bu") or "").lower()
        tail = text[m.end(): m.end() + 14]
        yearly = bool(_YEARLY.search(tail))
        if unit in ("lpa", "lakh", "lakhs"):
            monthly = value * 100_000 / 12
        else:
            value *= 1000 if unit == "k" else 1
            monthly = value / 12 if yearly else value
        shown_end = m.end() + (len(tail.split(".")[0].rstrip()) if (yearly or "month" in tail.lower()) else 0)
        return monthly, text[m.start(): shown_end].strip()
    return None


def extract_city(text: str):
    m = _CITY.search(text)
    return CITIES[m.group(1).lower()] if m else None


def _company_mismatch(a: str, b: str) -> bool:
    la, lb = a.lower(), b.lower()
    if la in lb or lb in la:
        return False
    return not ({t for t in core_tokens(a) if len(t) >= 4} & {t for t in core_tokens(b) if len(t) >= 4})


def run(ctx, serp=None):
    j = ctx.journey
    lt = (j.listing.text or "").strip() if j and j.listing else ""
    ot = (j.offer_text or "").strip() if j else ""
    if not lt or not ot:
        return result(ID, TITLE, WEIGHT, "unknown", "Needs both the listing text and the offer text to compare them.")
    le, oe = extract(lt), extract(ot)
    diffs, same, flags = [], [], []
    fail = False

    if le.company and oe.company:
        if _company_mismatch(le.company, oe.company):
            fail = True
            flags.append("COMPANY_MISMATCH")
            diffs.append(f"Listing said the company is {le.company}, offer says {oe.company}.")
        else:
            same.append("company")
    ls, os_ = _stems(le.role or ""), _stems(oe.role or "")
    if ls and os_:
        if len(ls & os_) / min(len(ls), len(os_)) < 0.5:
            diffs.append(f"Listing said the role is {le.role}, offer says {oe.role}.")
        else:
            same.append("role")
    lp, op = extract_pay(lt), extract_pay(ot)
    if lp and op:
        if abs(lp[0] - op[0]) / max(lp[0], op[0]) > 0.25:
            diffs.append(f"Listing said pay is {lp[1]}, offer says {op[1]}.")
        else:
            same.append("pay")
    lc, oc = extract_city(lt), extract_city(ot)
    if lc and oc:
        if lc != oc:
            diffs.append(f"Listing said the location is {lc}, offer says {oc}.")
        else:
            same.append("location")

    if len(diffs) + len(same) < 2:
        return result(ID, TITLE, WEIGHT, "unknown", "Too little in common to compare the listing with the offer.")
    if fail:
        return result(ID, TITLE, WEIGHT, "fail", " ".join(diffs), flags=flags)
    if diffs:
        return result(ID, TITLE, WEIGHT, "warn", " ".join(diffs))
    return result(ID, TITLE, WEIGHT, "pass", f"The listing and the offer agree on {', '.join(same)}.")
