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
# Job boards list real roles for many companies, so a role-title phrase always matches them. That is not
# "the same text under another name"; they are ignored for reuse (scam keywords on them still count).
JOB_BOARDS = {
    "internshala.com", "indeed.com", "naukri.com", "linkedin.com", "glassdoor.com", "glassdoor.co.in", "shine.com",
    "monsterindia.com", "foundit.in", "freshersworld.com", "apna.co", "jooble.org", "ziprecruiter.com",
    "simplyhired.com", "timesjobs.com", "hirist.tech", "wellfound.com", "cutshort.io", "letsintern.com", "ambitionbox.com",
}
_WORD = re.compile(r"[\w'’-]+")


def _norm(text: str) -> str:
    """Lowercase words only, single-spaced, so punctuation and spacing can't hide a verbatim match."""
    return " ".join(_WORD.findall(text.lower()))


# "Software Engineer at Acme Corp", "by Acme", "| Acme Labs": a capitalised name after a company-introducing word
_NAMED = re.compile(r"(?:\bat|\bby|\bfrom|\bwith|\bjoin|@|\|)\s+([A-Z][\w&.]*(?:\s+[A-Z][\w&.]*){0,3})")
_NOT_A_COMPANY = {"internship", "intern", "interns", "jobs", "job", "india", "remote", "home", "work", "fresher", "freshers",
                  "students", "student", "apply", "today", "online", "hiring", "career", "careers", "mumbai", "delhi",
                  "bengaluru", "bangalore", "pune", "hyderabad", "chennai", "noida", "gurgaon", "gurugram", "kolkata"}


def _classify(ctx, blob: str, domain: str) -> str | None:
    if any(w in blob for w in SCAM_WORDS) or domain in COMPLAINT_SITES:
        return "scam_report"
    if ctx.trusted and domain in {registrable(t) for t in ctx.trusted}:
        return "official"
    if domain in JOB_BOARDS:
        return None
    # "other names" only makes sense when we know which name the offer claims
    if ctx.company and not any(t in blob for t in core_tokens(ctx.company)):
        return "reused"
    return None


def names_other_company(ctx, raw: str) -> bool:
    """Heuristic: the title/snippet introduces a capitalised company name that isn't ours."""
    ours = set(core_tokens(ctx.company or ""))
    for m in _NAMED.finditer(raw):
        toks = [t for t in core_tokens(m.group(1)) if len(t) >= 4 and t not in _NOT_A_COMPANY]
        if toks and not (set(toks) & ours):
            return True
    return False


def trace(ctx, serp, text, extracted, *, id, title, weight, other_company_rule=False):
    """Shared by the offer's wording trace and the listing's clone detection."""
    phrases = select_phrases(text, extracted)
    if not phrases:
        return result(id, title, weight, "unknown", "The message is too short or too generic to fingerprint.", engine=ENGINE)
    queries, hits = [], {"scam_report": [], "reused": [], "official": []}
    for ph in phrases:
        q = f'"{ph}"'
        queries.append(q)
        res = serp.search({"engine": "google", "q": q})
        want = _norm(ph)
        for r in res.data.get("organic_results", []):
            blob = f"{r.get('title', '')} {r.get('snippet', '')}".lower()
            if want not in _norm(blob):
                # Google relaxes quotes and returns pages that merely share words with the phrase. A page counts
                # only if the phrase itself appears (punctuation and case aside); otherwise a scam keyword on a
                # loosely related page could force HIGH RISK.
                continue
            domain = registrable(r.get("link", ""))
            kind = _classify(ctx, blob, domain)
            if kind:
                hits[kind].append((domain, ev(res, r.get("title", ""), r.get("link", ""), r.get("snippet", ""), kind)))
    meta = dict(engine=ENGINE, query=" | ".join(queries), phrases=phrases)
    if hits["scam_report"]:
        return result(id, title, weight, "fail", "This exact wording appears in scam reports online.",
                      evidence=[e for _, e in hits["scam_report"]], **meta)
    if other_company_rule and not hits["official"]:
        other = [e for _, e in hits["reused"] if names_other_company(ctx, f"{e.title} {e.snippet}")]
        if other:
            return result(id, title, weight, "warn", "This listing's text also appears under another company's name.",
                          evidence=other, **meta)
    if len({d for d, _ in hits["reused"]}) >= 2 and not hits["official"]:
        return result(id, title, weight, "warn",
                      "This exact wording appears on other sites under different names — typical of mass-produced offers.",
                      evidence=[e for _, e in hits["reused"]], **meta)
    if hits["official"]:
        return result(id, title, weight, "pass", "The wording matches the company's own pages.",
                      evidence=[e for _, e in hits["official"]], **meta)
    return result(id, title, weight, "unknown", "The wording isn't found elsewhere online. That's not evidence either way.", **meta)


def run(ctx, serp):
    ex = ctx.extracted or Extracted(company=ctx.company, sender_email=ctx.sender_email)
    return trace(ctx, serp, ctx.text, ex, id=ID, title=TITLE, weight=WEIGHT)
