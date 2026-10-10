"""Is the company in an Indian company registry (MCA/CIN aggregators)?"""
from ..extract import core_tokens
from . import ev, result
from .sender_identity import registrable

ID, TITLE, WEIGHT, ENGINE = "registration", "Company registration", 5, "google"
REGISTRIES = {"zaubacorp.com", "tofler.in", "thecompanycheck.com"}


def run(ctx, serp):
    if not ctx.company:
        return result(ID, TITLE, WEIGHT, "unknown", "No company identified.", engine=ENGINE)
    q = f"{ctx.company} CIN site:zaubacorp.com OR site:tofler.in OR site:thecompanycheck.com"
    hit = serp.search({"engine": "google", "q": q})
    toks = core_tokens(ctx.company)
    found = [
        ev(hit, r.get("title", ""), r["link"], r.get("snippet", ""))
        for r in hit.data.get("organic_results", [])
        if registrable(r.get("link", "")) in REGISTRIES and any(t in r.get("title", "").lower() for t in toks)
    ]
    if found:
        return result(ID, TITLE, WEIGHT, "pass", "A company with this name appears in an Indian company registry.", engine=ENGINE, query=q, evidence=found)
    return result(ID, TITLE, WEIGHT, "warn", "No registry entry found for this name.", engine=ENGINE, query=q)
