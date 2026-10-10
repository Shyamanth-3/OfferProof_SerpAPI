import asyncio
import logging
import os
import time

from . import policy, privacy
from .checks import company_fraud_notice, identifier_trace, impersonation_context, job_listing, registration, sender_identity, text_red_flags
from .checks import result
from .extract import extract
from .models import CheckRequest, CheckResponse, Ctx
from .serp import CacheMiss, Serp

log = logging.getLogger("offerproof")
CHECK_TIMEOUT = float(os.getenv("SEARCH_TIMEOUT_SECONDS", "8"))
STAGE1 = [sender_identity, impersonation_context, job_listing, registration, text_red_flags]
STAGE2 = [company_fraud_notice, identifier_trace]  # need the official domain from stage 1
ORDER = [sender_identity, identifier_trace, company_fraud_notice, impersonation_context, job_listing, registration, text_red_flags]


async def _run(mod, ctx, serp):
    try:
        return await asyncio.wait_for(asyncio.to_thread(mod.run, ctx, serp), CHECK_TIMEOUT)
    except CacheMiss:
        why = "No recorded search for this offer (cached mode)."
    except asyncio.TimeoutError:
        log.warning("%s timed out", mod.ID)
        why = "The search timed out, so this check was skipped."
    except Exception as e:
        log.warning("%s failed: %r", mod.ID, e)
        why = "The search failed, so this check was skipped."
    return result(mod.ID, mod.TITLE, mod.WEIGHT, "unknown", why, engine=mod.ENGINE)


async def check(req: CheckRequest, mode: str) -> CheckResponse:
    t0 = time.monotonic()
    text, redacted = privacy.redact(req.offer_text)  # only redacted text is used from here on
    ex = extract(text, req.company, req.sender_email, req.role)
    ctx = Ctx(text, ex.company, ex.role, ex.sender_email, ex.identifiers)
    serp = Serp(mode)

    results = dict(zip((m.ID for m in STAGE1), await asyncio.gather(*(_run(m, ctx, serp) for m in STAGE1))))
    s = results["sender_identity"]
    ctx.official = s.meta.get("official", [])
    ctx.sender_on_official = s.status == "pass"
    trusted = ctx.trusted = s.meta.get("trusted", [])
    results.update(zip((m.ID for m in STAGE2), await asyncio.gather(*(_run(m, ctx, serp) for m in STAGE2))))

    checks = [results[m.ID] for m in ORDER]
    d = policy.decide(checks)
    return CheckResponse(
        **d, extracted=ex, redacted=redacted, checks=checks,
        next_steps=policy.next_steps(d["verdict"], trusted[0] if trusted else None),
        searches_used=serp.used, elapsed_ms=round((time.monotonic() - t0) * 1000), mode=mode,
    )
