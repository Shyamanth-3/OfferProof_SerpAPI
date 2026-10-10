"""Investigate the full recruitment journey: the existing checks, the journey checks, and a timeline.

Nothing here fetches a URL. The listing URL is used only as text (its domain). All stage text goes through
privacy.redact first. Rules decide; there is no model anywhere.
"""
import asyncio
import re
import time

from . import pipeline, policy, privacy, verify_kit
from .checks import result, template_trace, text_red_flags
from .checks.sender_identity import ATS
from .extract import FREE_MAIL, extract
from .fingerprint import select_phrases
from .models import (Ctx, Divergence, Extracted, Identifiers, InterviewStage, JourneyInput, JourneyResponse,
                     ListingStage, RecruiterStage, TimelineNode)
from .registry import JOURNEY_ORDER, JOURNEY_STAGE1, JOURNEY_STAGE2, JOURNEY_TOTAL_WEIGHT

TEXT_CHECKS = {text_red_flags.ID, template_trace.ID}  # need offer text; with none they are unknown, never "pass"

# stage -> (checks whose fail/warn/pass decide the stage, checks shown for it). Checks whose warn only means
# "couldn't confirm" (job listing, registry) and info-only checks are shown but don't make a stage "diverge".
STAGES = [
    ("listing", ["listing_source", "listing_clone"], ["listing_source", "listing_clone", "official_careers"]),
    ("recruiter", ["sender_identity", "identifier_trace"], ["sender_identity", "identifier_trace", "recruiter_trace"]),
    ("interview", ["interview_process"], ["interview_process"]),
    ("payment", [], ["interview_process", "text_red_flags"]),
    ("offer", ["text_red_flags", "template_trace", "listing_offer_consistency"],
     ["text_red_flags", "template_trace", "listing_offer_consistency", "job_listing", "registration"]),
]
_RANK = {"fail": 2, "warn": 1}
_CHANNEL = {"whatsapp": "WhatsApp", "telegram": "Telegram"}


def _redact(inp: JourneyInput) -> tuple[JourneyInput, list[str]]:
    kinds: list[str] = []

    def r(v):
        if not v or not v.strip():
            return None
        text, k = privacy.redact(v)
        kinds.extend(k)
        return text.strip()

    l, rc, iv = inp.listing, inp.recruiter, inp.interview
    clean = JourneyInput(
        company=r(inp.company), role=r(inp.role), offer_text=r(inp.offer_text),
        listing=ListingStage(url=r(l.url), text=r(l.text)) if l else None,
        recruiter=RecruiterStage(name=r(rc.name), email=r(rc.email), phone=r(rc.phone), channel=rc.channel) if rc else None,
        interview=InterviewStage(**iv.model_dump()) if iv else None,
    )
    return clean, list(dict.fromkeys(kinds))


def _brand_from_email(email: str | None) -> str | None:
    if not email or "@" not in email:
        return None
    dom = email.split("@")[1].lower()
    label = dom.split(".")[0]
    if dom in FREE_MAIL or any(dom == a or dom.endswith("." + a) for a in ATS) or len(label) < 4 or not label.isalnum():
        return None
    return label.capitalize()


def _merge(*parts: Identifiers, phone: str | None, email: str | None) -> Identifiers:
    out = {k: [] for k in ("upi", "phones", "telegram", "emails", "links")}
    for p in parts:
        for k in out:
            out[k] += getattr(p, k)
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) >= 10 and digits[-10] in "6789":
        out["phones"].append(digits[-10:])
    if email:
        out["emails"].append(email.lower())
    return Identifiers(**{k: list(dict.fromkeys(v)) for k, v in out.items()})


def build_ctx(inp: JourneyInput) -> Ctx:
    offer = inp.offer_text or ""
    ltext = inp.listing.text if inp.listing and inp.listing.text else ""
    oe = extract(offer) if offer else Extracted()
    le = extract(ltext) if ltext else Extracted()
    email = ((inp.recruiter.email or "").strip().lower() or None) if inp.recruiter else None  # same normalisation as /api/check
    # company: the field, else the offer, else the listing, else the recruiter email's domain
    company = inp.company or oe.company or le.company or _brand_from_email(email)
    role = inp.role or le.role or oe.role  # the listing is the better source for the role
    sender = email or oe.sender_email
    ids = _merge(oe.identifiers, le.identifiers, phone=inp.recruiter.phone if inp.recruiter else None, email=email)
    ex = Extracted(company=company, sender_email=sender, role=role, identifiers=ids)
    ex.fingerprint = select_phrases(offer, ex) if offer else []
    return Ctx(offer, company, role, sender, ids, extracted=ex, journey=inp)


async def _run(mod, ctx, serp):
    if mod.ID in TEXT_CHECKS and not ctx.text.strip():
        return result(mod.ID, mod.TITLE, mod.WEIGHT, "unknown", "No offer text was given.", engine=mod.ENGINE)
    return await pipeline._run(mod, ctx, serp)


def _first_sentence(s: str) -> str:
    return re.split(r"(?<=[.!?])\s", s.strip(), maxsplit=1)[0]


def _node(stage, status, headline, shown, results) -> TimelineNode:
    return TimelineNode(stage=stage, status=status, headline=headline, check_ids=[c for c in shown if c in results])


def build_timeline(inp: JourneyInput, results: dict, overrides) -> tuple[list[TimelineNode], Divergence | None]:
    rc, iv = inp.recruiter, inp.interview
    present = {
        "listing": bool(inp.listing and inp.listing.has_content()),
        "recruiter": bool(rc and rc.has_content()),
        "interview": bool(iv and iv.has_content()),
        "offer": bool(inp.offer_text),
    }
    nodes = []
    for stage, drivers, shown in STAGES:
        if stage == "payment":
            asked = iv.asked_to_pay if iv else None
            any_text = bool(inp.listing and inp.listing.text) or bool(inp.offer_text)
            paid = any(o.rule == "PAYMENT_IN_PROCESS" for o in overrides)
            if not (asked is not None or any_text):
                nodes.append(_node(stage, "not_provided", "You didn't give details for this stage.", shown, results))
            elif paid:
                said = "You were asked to pay during hiring." if asked else "The text you gave us demands a payment."
                nodes.append(_node(stage, "diverges", said, shown, results))
            elif asked is False:
                nodes.append(_node(stage, "matches", "You weren't asked to pay, and no fee is demanded in the text you gave us.", shown, results))
            else:
                nodes.append(_node(stage, "unverified", "We couldn't tell whether you were asked to pay.", shown, results))
            continue
        if not present[stage]:
            nodes.append(_node(stage, "not_provided", "You didn't give details for this stage.", shown, results))
            continue
        scored = [results[c] for c in drivers if c in results and results[c].status in ("pass", "warn", "fail")]
        bad = [(_RANK[c.status], c.weight, _first_sentence(c.finding)) for c in scored if c.status in _RANK]
        if stage == "recruiter" and rc.channel in _CHANNEL and results["sender_identity"].status != "pass":
            bad.append((1, 0, f"You were contacted on {_CHANNEL[rc.channel]} with no email from the company's own domain."))
        if bad:  # the strongest finding: fail beats warn, higher weight wins ties
            nodes.append(_node(stage, "diverges", max(bad)[2], shown, results))
        elif scored:
            nodes.append(_node(stage, "matches", _first_sentence(scored[0].finding), shown, results))
        else:
            nodes.append(_node(stage, "unverified", "We couldn't confirm this stage with the evidence available.", shown, results))
    first = next((n for n in nodes if n.status == "diverges"), None)  # STAGES is already in journey order
    return nodes, (Divergence(stage=first.stage, reason=first.headline) if first else None)


async def investigate(req: JourneyInput, mode: str) -> JourneyResponse:
    t0 = time.monotonic()
    inp, redacted = _redact(req)
    ctx = build_ctx(inp)
    serp = pipeline.Serp(mode)

    results = dict(zip((m.ID for m in JOURNEY_STAGE1), await asyncio.gather(*(_run(m, ctx, serp) for m in JOURNEY_STAGE1))))
    s = results["sender_identity"]
    ctx.official = s.meta.get("official", [])
    ctx.sender_on_official = s.status == "pass"
    trusted = ctx.trusted = s.meta.get("trusted", [])
    results.update(zip((m.ID for m in JOURNEY_STAGE2), await asyncio.gather(*(_run(m, ctx, serp) for m in JOURNEY_STAGE2))))

    checks = [results[m.ID] for m in JOURNEY_ORDER]
    d = policy.decide(checks, JOURNEY_TOTAL_WEIGHT)
    timeline, first = build_timeline(inp, results, d["overrides"])
    return JourneyResponse(
        **d, extracted=ctx.extracted, redacted=redacted, checks=checks,
        next_steps=policy.next_steps(d["verdict"], trusted[0] if trusted else None),
        verify_kit=verify_kit.build(ctx, results),
        searches_used=serp.used, elapsed_ms=round((time.monotonic() - t0) * 1000), mode=mode,
        timeline=timeline, first_divergence=first,
    )
