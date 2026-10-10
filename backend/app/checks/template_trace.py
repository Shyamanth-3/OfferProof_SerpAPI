"""Search the offer's own wording as an exact phrase: mass-produced scam templates reappear online."""
import re

from ..extract import core_tokens
from ..fingerprint import select_phrases
from ..models import Extracted
from . import ev, result
from .sender_identity import registrable

ID, TITLE, WEIGHT, ENGINE = "template_trace", "Wording trace", 20, "google"
SCAM_WORDS = ("scam", "fraud", "fake", "cheated", "beware", "not genuine", "money lost", "cyber crime",
              "consumer complaint", "complaint against")
COMPLAINT_SITES = {"consumercomplaints.in", "voxya.com", "complaintboard.in", "mouthshut.com"}
_WORD = re.compile(r"[\w'’-]+")


def _classify(ctx, blob: str, domain: str) -> str | None:
    if any(w in blob for w in SCAM_WORDS) or domain in COMPLAINT_SITES:
        return "scam_report"
    if ctx.trusted and domain in {registrable(t) for t in ctx.trusted}:
        return "official"
    # "other names" only makes sense when we know which name the offer claims
    if ctx.company and not any(t in blob for t in core_tokens(ctx.company)):
        return "reused"
    return None


def run(ctx, serp):
    ex = ctx.extracted or Extracted(company=ctx.company, sender_email=ctx.sender_email)
    phrases = select_phrases(ctx.text, ex)
    if not phrases:
        return result(ID, TITLE, WEIGHT, "unknown", "The message is too short or too generic to fingerprint.", engine=ENGINE)
    queries, hits = [], {"scam_report": [], "reused": [], "official": []}
    for ph in phrases:
        q = f'"{ph}"'
        queries.append(q)
        res = serp.search({"engine": "google", "q": q})
        need = {w.lower() for w in _WORD.findall(ph)}
        for r in res.data.get("organic_results", []):
            blob = f"{r.get('title', '')} {r.get('snippet', '')}".lower()
            if len(need & set(_WORD.findall(blob))) / len(need) < 0.6:
                continue  # the page doesn't really contain this wording
            domain = registrable(r.get("link", ""))
            kind = _classify(ctx, blob, domain)
            if kind:
                hits[kind].append((domain, ev(res, r.get("title", ""), r.get("link", ""), r.get("snippet", ""), kind)))
    meta = dict(engine=ENGINE, query=" | ".join(queries), phrases=phrases)
    if hits["scam_report"]:
        return result(ID, TITLE, WEIGHT, "fail", "This exact wording appears in scam reports online.",
                      evidence=[e for _, e in hits["scam_report"]], **meta)
    if len({d for d, _ in hits["reused"]}) >= 2 and not hits["official"]:
        return result(ID, TITLE, WEIGHT, "warn",
                      "This exact wording appears on other sites under different names — typical of mass-produced offers.",
                      evidence=[e for _, e in hits["reused"]], **meta)
    if hits["official"]:
        return result(ID, TITLE, WEIGHT, "pass", "The wording matches the company's own pages.",
                      evidence=[e for _, e in hits["official"]], **meta)
    return result(ID, TITLE, WEIGHT, "unknown", "The wording isn't found elsewhere online. That's not evidence either way.", **meta)
