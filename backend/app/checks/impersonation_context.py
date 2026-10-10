"""Is this brand often impersonated? Context only: never evidence against this offer."""
from ..extract import core_tokens
from . import ev, result

ID, TITLE, WEIGHT, ENGINE = "impersonation_context", "Brand impersonation context", 0, "google_news"
WORDS = ("fake", "scam", "fraud", "impersonat")


def run(ctx, serp):
    if not ctx.company:
        return result(ID, TITLE, WEIGHT, "unknown", "No company identified.", engine=ENGINE)
    q = f"{ctx.company} fake job offer"
    hit = serp.search({"engine": "google_news", "q": q})
    toks = core_tokens(ctx.company)
    found = []
    for r in hit.data.get("news_results", []):
        blob = f"{r.get('title', '')} {r.get('snippet', '')}".lower()
        if any(t in blob for t in toks) and any(w in blob for w in WORDS):
            found.append(ev(hit, r.get("title", ""), r.get("link", ""), r.get("snippet", "")))
    if found:
        return result(ID, TITLE, WEIGHT, "info", "This brand is frequently impersonated by scammers. Context only — it says nothing about this specific offer.",
                      engine=ENGINE, query=q, evidence=found)
    return result(ID, TITLE, WEIGHT, "unknown", "No recent news about fake offers using this brand.", engine=ENGINE, query=q)
