"""Where is the company's own careers page, and does it list this role? Informational: weight 0, never scored."""
import re
from urllib.parse import urlparse

from ..fingerprint import STOP
from . import ev, result
from .sender_identity import registrable

ID, TITLE, WEIGHT, ENGINE = "official_careers", "Official careers page", 0, "google"
_CAREER = re.compile(r"career|jobs|join", re.I)


def _stems(text: str) -> set[str]:
    # first 5 letters, so "engineer" matches "engineering"
    return {w[:5] for w in re.findall(r"[a-z]{3,}", text.lower()) if w not in STOP}


def run(ctx, serp):
    if not ctx.official_domain_trusted:
        return result(ID, TITLE, WEIGHT, "unknown", "No confirmed official website, so we can't point you to its careers page.", engine=ENGINE)
    dom = ctx.trusted[0]
    q = f"site:{dom} (careers OR jobs) {ctx.role}" if ctx.role else f"site:{dom} careers"
    hit = serp.search({"engine": "google", "q": q})
    on_site = [r for r in hit.data.get("organic_results", []) if r.get("link") and registrable(r["link"]) == registrable(dom)]
    careers = next((r for r in on_site if _CAREER.search(urlparse(r["link"]).netloc + urlparse(r["link"]).path)), on_site[0] if on_site else None)

    role = _stems(ctx.role or "")
    role_hits = [r for r in on_site if role and len(role & _stems(f"{r.get('title', '')} {r.get('snippet', '')}")) / len(role) >= 0.6]
    meta = dict(engine=ENGINE, query=q, careers_url=careers["link"] if careers else None,
                role_on_official_site=(bool(role_hits) if role else None), official_domain=dom)
    if role_hits:
        shown = [ev(hit, r.get("title", ""), r["link"], r.get("snippet", "")) for r in role_hits]
        return result(ID, TITLE, WEIGHT, "info", "This role appears on the company's official site.", evidence=shown, **meta)
    if careers:
        e = [ev(hit, careers.get("title", ""), careers["link"], careers.get("snippet", ""))]
        finding = "We found the company's careers page, but not this exact role." if role else "We found the company's careers page."
        return result(ID, TITLE, WEIGHT, "info", finding, evidence=e, **meta)
    return result(ID, TITLE, WEIGHT, "info", f"Search found no careers page on {dom}. Check the site directly.", **meta)
