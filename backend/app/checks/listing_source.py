"""Where did the student see the job? Judged from the listing URL's domain only. The URL is NEVER fetched."""
from urllib.parse import urlparse

from . import result
from .sender_identity import _matches, is_lookalike, registrable

ID, TITLE, WEIGHT, ENGINE = "listing_source", "Where the job was listed", 10, None
JOB_BOARDS = {
    "naukri.com", "linkedin.com", "internshala.com", "indeed.com", "foundit.in", "glassdoor.co.in",
    "unstop.com", "instahyre.com", "wellfound.com",
}


def url_host(url: str) -> str:
    """Hostname of a pasted URL, with or without a scheme. Text parsing only; nothing is requested."""
    u = url.strip()
    host = urlparse(u if "//" in u else f"//{u}").hostname or ""
    return host.lower().removeprefix("www.")


def run(ctx, serp=None):
    listing = ctx.journey.listing if ctx.journey else None
    url = (listing.url or "").strip() if listing else ""
    if not url:
        return result(ID, TITLE, WEIGHT, "unknown", "No listing link was given.")
    host = url_host(url)
    if not host or "." not in host:
        return result(ID, TITLE, WEIGHT, "unknown", "That doesn't look like a web address, so we couldn't judge where it was listed.")
    dom = registrable(host)
    meta = dict(listing_domain=dom)

    if ctx.trusted and _matches(host, ctx.trusted):
        return result(ID, TITLE, WEIGHT, "pass", "Listed on the company's own site.", **meta)
    if dom in JOB_BOARDS:
        return result(ID, TITLE, WEIGHT, "info", "Posted on a job board — check it also appears on the company's careers page.", **meta)
    known = ctx.trusted or ctx.official
    for o in known:
        if is_lookalike(host, o):
            return result(ID, TITLE, WEIGHT, "fail", f"The listing is on {dom}, which imitates the company's domain {registrable(o)}.", **meta)
    if ctx.official and not ctx.trusted and _matches(host, ctx.official):
        return result(ID, TITLE, WEIGHT, "warn", "The listing matches the top search result for this company, but we couldn't confirm that site is official.", **meta)
    if known:
        return result(ID, TITLE, WEIGHT, "warn", "Listed on a site that isn't the company's.", **meta)
    return result(ID, TITLE, WEIGHT, "unknown", "No confirmed official website for this company, so we can't compare where it was listed.", **meta)
