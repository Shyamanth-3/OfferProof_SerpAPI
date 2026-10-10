"""Does the company's own site warn about fake offers? Context only (weight 0)."""
from . import ev, result
from .sender_identity import registrable

ID, TITLE, WEIGHT, ENGINE = "company_fraud_notice", "Company fraud notice", 0, "google"
WORDS = ("fraud", "fake", "never charge", "scam", "beware", "do not pay", "does not charge")


def run(ctx, serp):
    if not ctx.official:
        return result(ID, TITLE, WEIGHT, "unknown", "No official website found, so the company's own warnings couldn't be searched.", engine=ENGINE)
    dom = ctx.official[0]
    q = f'site:{dom} (fraud OR fake OR "never charge" OR "recruitment scam" OR "beware")'
    hit = serp.search({"engine": "google", "q": q})
    found = [
        ev(hit, r.get("title", ""), r["link"], r.get("snippet", ""))
        for r in hit.data.get("organic_results", [])
        if registrable(r.get("link", "")) == registrable(dom)
        and any(w in f"{r.get('title', '')} {r.get('snippet', '')}".lower() for w in WORDS)
    ]
    if found:
        return result(ID, TITLE, WEIGHT, "info", "The company publicly warns about fake offers.", engine=ENGINE, query=q, evidence=found, notice_found=True)
    return result(ID, TITLE, WEIGHT, "unknown", f"No fraud notice found on {dom}. That doesn't mean there isn't one.", engine=ENGINE, query=q)
