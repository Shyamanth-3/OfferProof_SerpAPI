"""Has this UPI ID / phone / Telegram handle / sender address been reported as a scam?"""
import re

from . import ev, result

ID, TITLE, WEIGHT, ENGINE = "identifier_trace", "Payment ID / contact trace", 25, "google"
SCAM_WORDS = ("scam", "fraud", "fake", "cheated", "beware", "not genuine", "money lost", "cyber crime")


def pick(ctx) -> list[tuple[str, str]]:
    """Up to 3 (needle, query term) in priority order: UPI, phone, Telegram, off-domain sender."""
    i = ctx.identifiers
    items = [(u, u) for u in i.upi] + [(p, p) for p in i.phones] + [(t.lower(), f"@{t}") for t in i.telegram]
    if ctx.sender_email and not ctx.sender_on_official:
        items.append((ctx.sender_email, ctx.sender_email))
    return items[:3]


def _mentions(needle: str, blob: str) -> bool:
    if needle.isdigit():
        return needle in re.sub(r"\D", "", blob)  # "98765 43210" and "+91-98765-43210" both count
    return needle in blob.lower()


def run(ctx, serp):
    items = pick(ctx)
    if not items:
        return result(ID, TITLE, WEIGHT, "unknown", "No payment ID, phone number, Telegram handle or off-domain sender to trace.", engine=ENGINE)
    queries, reported, mentioned = [], [], []
    for needle, term in items:
        q = f'"{term}"'
        queries.append(q)
        hit = serp.search({"engine": "google", "q": q})
        for r in hit.data.get("organic_results", []):
            blob = f"{r.get('title', '')} {r.get('snippet', '')}"
            if not _mentions(needle, blob):
                continue
            e = ev(hit, r.get("title", ""), r.get("link", ""), r.get("snippet", ""))
            (reported if any(w in blob.lower() for w in SCAM_WORDS) else mentioned).append(e)
    query = " | ".join(queries)
    if reported:
        return result(ID, TITLE, WEIGHT, "fail", "A payment ID, number or handle from this message appears in pages that call it a scam.",
                      engine=ENGINE, query=query, evidence=reported)
    if mentioned:
        return result(ID, TITLE, WEIGHT, "info", "This identifier appears online in unrelated pages.", engine=ENGINE, query=query, evidence=mentioned)
    return result(ID, TITLE, WEIGHT, "unknown", "No public reports found. That is NOT evidence the offer is safe.", engine=ENGINE, query=query)
