"""'Verify it yourself': a fixed message and the official careers link. Pure: no network, nothing generated.

Hard rule: every linkable or actionable field (official_domain, careers_url, mailto, advice) comes only
from the TRUSTED official domain. The message may quote the sender's address and UPI ID as plain text
so the company can recognise the mail, but it never contains a link or a phone number, and never the
student's name, phone, email, Aadhaar or PAN.
"""
import re
from urllib.parse import quote

from .checks.text_red_flags import detect, sentences
from .models import VerifyKit

_AMOUNT = re.compile(r"(?:₹|\brs\b\.?|\binr\b)\s*([\d,]+(?:\.\d+)?)", re.I)

ADVICE_TRUSTED = "Contact the company only through its official website, not through any link, number or email in the offer."
ADVICE_UNTRUSTED = ("We couldn't confirm the company's official website. Look it up yourself — "
                    "don't use any link, number or email from the message.")


def fee_amount(text: str) -> str | None:
    """The amount in the same sentence as the fee demand (not the stipend)."""
    phrases = detect(text).get("FEE", [])
    for s in sentences(text):
        if any(p in s for p in phrases):
            m = _AMOUNT.search(s)
            if m:
                return m.group(1)
    return None


def build_message(ctx, fee: bool) -> str:
    company = ctx.company or "your company"
    role = ctx.role or "an open position"
    sender = ctx.sender_email or "a WhatsApp/Telegram contact"
    upi = ctx.identifiers.upi[0] if ctx.identifiers.upi else None
    msg = f"Hello, I received a job offer that claims to be from {company} for the role of {role}. It was sent by {sender}"
    if fee:
        amount = fee_amount(ctx.text)
        msg += f", and it asks for a payment of ₹{amount}" if amount else ", and it asks for a payment"
    if upi:
        msg += f" to the UPI ID {upi}"
    return msg + ". Could you please confirm whether this offer is genuine? Thank you."


def build(ctx, checks: dict) -> VerifyKit:
    trusted = ctx.official_domain_trusted
    fee = "FEE" in (checks["text_red_flags"].flags if "text_red_flags" in checks else [])
    message = build_message(ctx, fee)
    careers = checks.get("official_careers")
    meta = careers.meta if (careers and trusted) else {}
    subject = f"Verifying a job offer from {ctx.company}" if ctx.company else "Verifying a job offer"
    return VerifyKit(
        official_domain=ctx.trusted[0] if trusted else None,
        trusted=trusted,
        careers_url=meta.get("careers_url"),
        role_on_official_site=meta.get("role_on_official_site"),
        message=message,
        mailto=f"mailto:?subject={quote(subject, safe='')}&body={quote(message, safe='')}" if trusted else None,
        advice=ADVICE_TRUSTED if trusted else ADVICE_UNTRUSTED,
    )
