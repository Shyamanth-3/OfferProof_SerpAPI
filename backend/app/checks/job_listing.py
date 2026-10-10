"""Is this role, at this company, posted anywhere public?"""
import re

from ..extract import core_tokens
from . import ev, result

ID, TITLE, WEIGHT, ENGINE = "job_listing", "Public job listing", 10, "google_jobs"
# role words too vague to confirm a role on their own
VAGUE = {"intern", "interns", "internship", "trainee", "associate", "junior", "senior", "program", "programme", "work", "from", "home", "with", "and", "the", "for"}


def _stems(text: str) -> set[str]:
    # first 5 letters, so "engineer" matches "engineering"
    return {t[:5] for t in re.findall(r"[a-z]{3,}", text.lower()) if t not in VAGUE}


def run(ctx, serp):
    if not ctx.company:
        return result(ID, TITLE, WEIGHT, "unknown", "No company identified, so no listing could be searched.", engine=ENGINE)
    q = f"{ctx.role or 'jobs'} {ctx.company}"
    hit = serp.search({"engine": "google_jobs", "q": q, "location": "India"})
    toks, role = core_tokens(ctx.company), _stems(ctx.role or "")
    same_co, same_role = [], []
    for j in hit.data.get("jobs_results", []):
        if not any(t in j.get("company_name", "").lower() for t in toks):
            continue
        link = j.get("share_link") or next((o.get("link") for o in j.get("apply_options", [])), "") or "https://www.google.com/search?q=" + q
        e = ev(hit, f"{j.get('title', '')} — {j.get('company_name', '')}", link, j.get("location", ""))
        same_co.append(e)
        if role & _stems(j.get("title", "")):
            same_role.append(e)
    if same_role:
        return result(ID, TITLE, WEIGHT, "pass", "A listing for this role at this company was found on Google Jobs.", engine=ENGINE, query=q, evidence=same_role)
    if same_co:
        why = f"none match the role “{ctx.role}”" if role else "the message names no specific role to match"
        return result(ID, TITLE, WEIGHT, "warn", f"Found other openings at this company, but {why}. That doesn't confirm this offer.", engine=ENGINE, query=q, evidence=same_co)
    return result(ID, TITLE, WEIGHT, "warn", "No matching public listing found. Many genuine roles aren't publicly listed.", engine=ENGINE, query=q)
