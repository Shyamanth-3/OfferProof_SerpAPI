import asyncio
import logging
import os
import time

import requests

from . import policy, privacy, verify_kit
from .checks import result
from .extract import extract
from .fingerprint import select_phrases
from .models import CheckRequest, CheckResponse, Ctx
from .registry import ORDER, STAGE1, STAGE2
from .serp import CacheMiss, CapReached, Serp

log = logging.getLogger("offerproof")
CHECK_TIMEOUT = float(os.getenv("SEARCH_TIMEOUT_SECONDS", "8"))


# SerpApi's own client timeout is a requests.Timeout, which is NOT an asyncio/builtin TimeoutError, so both are listed.
# Without this a slow search was reported as "The search failed". SerpApi often answers in 10-60 s, well past our limit.
SLOW = (asyncio.TimeoutError, requests.exceptions.Timeout)


async def _run(mod, ctx, serp):
    try:
        return await asyncio.wait_for(asyncio.to_thread(mod.run, ctx, serp), CHECK_TIMEOUT)
    except CapReached:
        why, skipped = "This site has reached its daily limit of live searches, so this check was skipped.", "capped"
    except CacheMiss:
        why, skipped = "No recorded search for this offer (cached mode).", "not_recorded"
    except SLOW as e:
        log.warning("%s was too slow: %r", mod.ID, e)
        why, skipped = "A search was too slow to finish, so this check was skipped. Running the check again usually works.", "slow"
    except Exception as e:
        log.warning("%s failed: %r", mod.ID, e)
        why, skipped = "The search failed, so this check was skipped.", "failed"
    res = result(mod.ID, mod.TITLE, mod.WEIGHT, "unknown", why, engine=mod.ENGINE)
    res.skipped = skipped
    return res


async def check(req: CheckRequest, mode: str) -> CheckResponse:
    t0 = time.monotonic()
    text, redacted = privacy.redact(req.offer_text)  # only redacted text is used from here on
    ex = extract(text, req.company, req.sender_email, req.role)
    ex.fingerprint = select_phrases(text, ex)
    ctx = Ctx(text, ex.company, ex.role, ex.sender_email, ex.identifiers, extracted=ex)
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
        verify_kit=verify_kit.build(ctx, results),
        next_steps=policy.next_steps(d["verdict"], trusted[0] if trusted else None),
        searches_used=serp.used, elapsed_ms=round((time.monotonic() - t0) * 1000), mode=mode,
    )
