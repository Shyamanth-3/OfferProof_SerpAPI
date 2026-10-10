"""Did hiring follow a real process? Rules on the student's own answers; one optional search on a trusted domain."""
from . import ev, result
from .sender_identity import registrable

ID, TITLE, WEIGHT, ENGINE = "interview_process", "Interview process", 15, "google"

_FORMAT = {
    "official_portal_or_video": "You interviewed through the company's official portal or a video call.",
    "other_video": "You interviewed on a video call.",
    "phone": "You interviewed by phone.",
}
_DOCS = "You were asked for Aadhaar, PAN or bank details before any offer. Genuine employers collect these only after a verified written offer."


def _official_process(ctx, serp):
    """Top result on the trusted official domain for the company's published hiring process, or None."""
    dom = ctx.trusted[0]
    q = f"site:{dom} recruitment process OR hiring process OR selection process"
    try:
        hit = serp.search({"engine": "google", "q": q})
    except Exception:  # the answer below doesn't depend on this search, so a failure just means no link
        return q, None
    for r in hit.data.get("organic_results", []):
        if r.get("link") and registrable(r["link"]) == registrable(dom):
            return q, ev(hit, r.get("title", ""), r["link"], r.get("snippet", ""))
    return q, None


def run(ctx, serp):
    iv = ctx.journey.interview if ctx.journey else None
    if iv is None or not iv.has_content():
        return result(ID, TITLE, WEIGHT, "unknown", "No interview details were given.", engine=ENGINE)

    flags, parts = [], []
    if iv.format in ("none", "chat_only"):
        status = "fail"
        flags.append("NO_REAL_INTERVIEW")
        parts.append("You said there was no interview. Genuine hiring includes at least one." if iv.format == "none"
                     else "You said hiring was done only over chat. Genuine hiring includes a real interview.")
    elif iv.format in _FORMAT:
        status = "pass"
        parts.append(_FORMAT[iv.format])
    else:
        status = "unknown"
        parts.append("You didn't say how the interview was held.")
    if iv.asked_for_documents_before_offer:
        flags.append("DOCS_BEFORE_OFFER")
        status = "fail" if status == "fail" else "warn"
        parts.append(_DOCS)
    if iv.asked_to_pay:
        flags.append("ASKED_TO_PAY")  # the verdict consequence is the PAYMENT_IN_PROCESS override, not this check
        parts.append("You also said you were asked to pay.")

    query, link = (None, None)
    if ctx.trusted:
        query, link = _official_process(ctx, serp)
        if link:
            parts.append("Compare with the company's published hiring process.")
    return result(ID, TITLE, WEIGHT, status, " ".join(parts), engine=ENGINE if query else None, query=query,
                  evidence=[link] if link else [], flags=flags, official_process_url=link.url if link else None,
                  asked_to_pay=bool(iv.asked_to_pay))
