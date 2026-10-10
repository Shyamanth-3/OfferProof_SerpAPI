"""Is the listing's own wording copied from somewhere else? Reuses the wording-trace logic on the listing text."""
from ..extract import extract
from ..models import Extracted
from . import result
from .template_trace import trace
from .text_red_flags import detect

ID, TITLE, WEIGHT, ENGINE = "listing_clone", "Listing wording trace", 15, "google"


def run(ctx, serp):
    listing = ctx.journey.listing if ctx.journey else None
    text = (listing.text or "").strip() if listing else ""
    if not text:
        return result(ID, TITLE, WEIGHT, "unknown", "No listing text was pasted.", engine=ENGINE)
    ex = extract(text, company=ctx.company) if ctx.company else Extracted()
    res = trace(ctx, serp, text, ex, id=ID, title=TITLE, weight=WEIGHT, other_company_rule=True)
    if "FEE" in detect(text):  # a fee in the listing counts as a payment demand at the listing stage
        res.flags = ["FEE"]
    return res
