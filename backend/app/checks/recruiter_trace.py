"""Does a public profile link this recruiter's name to the company? Context only: never pass, never fail."""
from ..extract import core_tokens
from . import ev, result

ID, TITLE, WEIGHT, ENGINE = "recruiter_trace", "Recruiter profile", 0, "google"


def run(ctx, serp):
    r = ctx.journey.recruiter if ctx.journey else None
    name = (r.name or "").strip() if r else ""
    if not name or not ctx.company:
        return result(ID, TITLE, WEIGHT, "unknown", "Needs the recruiter's name and the company to look for a public profile.", engine=ENGINE)
    q = f'site:linkedin.com/in "{name}" "{ctx.company}"'
    hit = serp.search({"engine": "google", "q": q})
    toks, lname = core_tokens(ctx.company), name.lower()
    for res in hit.data.get("organic_results", []):
        title = res.get("title", "")
        low = title.lower()
        if lname in low and any(t in low for t in toks):
            # only the title and link are kept; nothing else about the person
            return result(ID, TITLE, WEIGHT, "info",
                          f"A public profile with this name lists {ctx.company}. Profiles can be faked — this doesn't confirm the person.",
                          engine=ENGINE, query=q, evidence=[ev(hit, title, res.get("link", ""), "")])
    return result(ID, TITLE, WEIGHT, "unknown", f"No public profile found linking this name to {ctx.company}.", engine=ENGINE, query=q)
