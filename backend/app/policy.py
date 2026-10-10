"""Fixed rules decide the verdict. No AI, no randomness."""
from typing import Optional

from .models import CheckResult, Override

RANK = {"NOT_ENOUGH_EVIDENCE": 0, "NO_RED_FLAGS": 1, "CAUTION": 2, "HIGH_RISK": 3}
LABELS = {
    "HIGH_RISK": "High risk — do not pay or share documents",
    "CAUTION": "Caution — verify directly with the company",
    "NO_RED_FLAGS": "No red flags found — still, never pay to get hired",
    "NOT_ENOUGH_EVIDENCE": "Not enough evidence — verify on the company's official careers page",
}
POINTS = {"pass": 0.0, "warn": 0.5, "fail": 1.0}


def _get(checks: list[CheckResult], id: str) -> Optional[CheckResult]:
    return next((c for c in checks if c.id == id), None)


def _meta(checks, id, key):
    c = _get(checks, id)
    return c.meta.get(key) if c else None


# Each rule: (checks) -> Override | None
def fee_demanded(checks):
    c = _get(checks, "text_red_flags")
    if c and "FEE" in c.flags:
        return Override(rule="FEE_DEMANDED", verdict="HIGH_RISK", reason="Genuine employers in India don't charge candidates to be hired.")


def lookalike_domain(checks):
    if _meta(checks, "sender_identity", "lookalike"):
        official = _meta(checks, "sender_identity", "lookalike_of")
        return Override(rule="LOOKALIKE_DOMAIN", verdict="HIGH_RISK", reason=f"The sender's domain imitates {official}.")


def identifier_reported(checks):
    c = _get(checks, "identifier_trace")
    if c and c.status == "fail":
        return Override(rule="IDENTIFIER_REPORTED", verdict="HIGH_RISK", reason="This payment ID / number has been publicly reported.")


def free_mail_sender(checks):
    if _meta(checks, "sender_identity", "free_mail"):
        high = _meta(checks, "company_fraud_notice", "notice_found")
        return Override(
            rule="FREE_MAIL_SENDER",
            verdict="HIGH_RISK" if high else "CAUTION",
            reason="The offer came from a free mail address, and the company says it only uses its own domain."
            if high else "The offer came from a free mail address, not the company's own domain.",
        )


def off_platform_only(checks):
    c, s = _get(checks, "text_red_flags"), _get(checks, "sender_identity")
    if c and "OFF_PLATFORM" in c.flags and not (s and s.status == "pass"):
        return Override(rule="OFF_PLATFORM_ONLY", verdict="CAUTION", reason="The message pushes you to Telegram/WhatsApp and doesn't come from the company's own domain.")


def third_party_sender(checks):
    # Only for brands on the known-company list, where we're sure which domains are theirs.
    c = _get(checks, "sender_identity")
    if c and c.meta.get("third_party") and c.meta.get("known_brand"):
        co, dom = c.meta["company"], c.meta["sender_domain"]
        return Override(rule="THIRD_PARTY_SENDER", verdict="CAUTION", reason=f"The offer names {co}, but it was sent from {dom}, which is not a {co} domain.")


def job_guarantee(checks):
    c = _get(checks, "text_red_flags")
    if c and "JOB_GUARANTEE" in c.flags:
        return Override(rule="JOB_GUARANTEE", verdict="CAUTION",
                        reason="No genuine employer can guarantee you a job. “Guaranteed placement” programs are usually paid courses sold as internships.")


RULES = [fee_demanded, lookalike_domain, identifier_reported, free_mail_sender, off_platform_only, third_party_sender, job_guarantee]


def decide(checks: list[CheckResult]) -> dict:
    scored = [c for c in checks if c.scored]  # unknown and info never count, for or against
    weight = sum(c.weight for c in scored)
    score = round(100 * sum(POINTS[c.status] * c.weight for c in scored) / weight) if weight else None
    coverage = weight / 100

    if coverage < 0.5:
        verdict = "NOT_ENOUGH_EVIDENCE"
    elif score >= 55:
        verdict = "HIGH_RISK"
    elif score >= 25:
        verdict = "CAUTION"
    else:
        verdict = "NO_RED_FLAGS"

    overrides = [o for r in RULES if (o := r(checks))]
    for o in overrides:  # overrides can only raise severity
        if RANK[o.verdict] > RANK[verdict]:
            verdict = o.verdict
    return {"verdict": verdict, "verdict_label": LABELS[verdict], "risk_score": score, "coverage": coverage, "overrides": overrides}


def next_steps(verdict: str, official: Optional[str]) -> list[str]:
    where = f" ({official})" if official else ""
    steps = [f"Check the role on the company's official careers page{where}."]
    if verdict == "HIGH_RISK":
        steps.append("Report it at cybercrime.gov.in or call 1930 (National Cyber Crime Helpline).")
    steps.append("Never share Aadhaar, PAN or bank details before a verified written offer.")
    return steps
