"""Checkpoint D: official careers lookup and the verify kit. Stubbed search, no network."""
import asyncio
import re
from urllib.parse import parse_qs, unquote, urlparse

import app.pipeline as pl
from app import policy
from app.checks import official_careers, result
from app.extract import extract
from app.models import CheckRequest, Ctx, Identifiers
from app.serp import Hit
from app.verify_kit import ADVICE_TRUSTED, ADVICE_UNTRUSTED, build, build_message


class Stub:
    used = 0
    keys: list = []

    def __init__(self, organic=None):
        self.organic, self.queries = organic or [], []

    def search(self, params):
        self.queries.append(params["q"])
        return Hit({"organic_results": self.organic}, "2026-01-01T00:00:00+00:00", False)


def mk(text="x", company="Infosys Limited", role="Software Engineer Intern", sender=None, trusted=("infosys.com",), upi=()):
    c = Ctx(text, company, role, sender, Identifiers(upi=list(upi)), official=list(trusted), trusted=list(trusted))
    c.extracted = extract(text, company=company)
    return c


def page(url, title, snippet=""):
    return {"title": title, "link": url, "snippet": snippet}


# ---- D1: official_careers ------------------------------------------------------------
def test_untrusted_domain_is_unknown_and_makes_no_search():
    stub = Stub()
    r = official_careers.run(mk(trusted=()), stub)
    assert r.status == "unknown" and "No confirmed official website" in r.finding and stub.queries == []


def test_query_shapes():
    stub = Stub()
    official_careers.run(mk(), stub)
    official_careers.run(mk(role=None), stub)
    assert stub.queries == ["site:infosys.com (careers OR jobs) Software Engineer Intern", "site:infosys.com careers"]


def test_role_found_on_official_site():
    org = [page("https://www.infosys.com/about", "About"), page("https://careers.infosys.com/job/1", "Software Engineer Intern - Infosys")]
    r = official_careers.run(mk(), Stub(org))
    assert r.status == "info" and r.meta["role_on_official_site"] is True
    assert r.meta["careers_url"] == "https://careers.infosys.com/job/1"  # path/subdomain containing 'career' wins over the first hit
    assert "appears" in r.finding


def test_careers_page_found_but_not_the_role():
    r = official_careers.run(mk(), Stub([page("https://www.infosys.com/careers", "Careers at Infosys", "Join our teams in finance")]))
    assert r.status == "info" and r.meta["role_on_official_site"] is False and "not this exact role" in r.finding


def test_results_on_other_domains_are_ignored_and_no_page_still_info():
    r = official_careers.run(mk(), Stub([page("https://evil.example/careers", "Software Engineer Intern")]))
    assert r.status == "info" and r.meta["careers_url"] is None and r.meta["role_on_official_site"] is False


def test_falls_back_to_first_official_result():
    r = official_careers.run(mk(role=None), Stub([page("https://www.infosys.com/about", "About us")]))
    assert r.meta["careers_url"] == "https://www.infosys.com/about" and r.meta["role_on_official_site"] is None


def test_careers_check_is_informational_only():
    base = [result("sender_identity", "s", 30, "warn", "x", trusted=[]), result("text_red_flags", "t", 30, "pass", "x"),
            result("job_listing", "j", 10, "warn", "x")]
    ref = policy.decide(base)
    for status in ("pass", "warn", "fail", "info", "unknown"):
        d = policy.decide(base + [result("official_careers", "c", official_careers.WEIGHT, status, "x")])
        assert (d["verdict"], d["risk_score"], d["coverage"]) == (ref["verdict"], ref["risk_score"], ref["coverage"]), status
    assert official_careers.WEIGHT == 0


# ---- D2: the verify kit --------------------------------------------------------------
FEE_TEXT = "Stipend Rs. 45,000 per month. Pay Rs. 1,999 refundable registration fee to ab@okaxis to join."


def test_message_template_with_fee_and_upi():
    c = mk(FEE_TEXT, company="Nexora Labs", role=None, sender=None, upi=["ab@okaxis"])
    assert build_message(c, fee=True) == (
        "Hello, I received a job offer that claims to be from Nexora Labs for the role of an open position. "
        "It was sent by a WhatsApp/Telegram contact, and it asks for a payment of ₹1,999 to the UPI ID ab@okaxis. "
        "Could you please confirm whether this offer is genuine? Thank you.")


def test_message_template_without_fee_or_upi():
    c = mk("Join us.", company="Infosys Limited", role="Systems Engineer", sender="hr@infosys.com")
    assert build_message(c, fee=False) == (
        "Hello, I received a job offer that claims to be from Infosys Limited for the role of Systems Engineer. "
        "It was sent by hr@infosys.com. Could you please confirm whether this offer is genuine? Thank you.")


def test_fee_without_a_stated_amount():
    msg = build_message(mk("Pay the registration fee at once.", sender="hr@x.example"), fee=True)
    assert "It was sent by hr@x.example, and it asks for a payment. Could you" in msg and "₹" not in msg


def kit(ctx, flags=()):
    checks = {"text_red_flags": result("text_red_flags", "t", 30, "pass", "x", flags=flags)}
    checks["official_careers"] = official_careers.run(ctx, Stub([page("https://careers.infosys.com/", "Careers at Infosys")]))
    return build(ctx, checks)


def test_untrusted_kit_has_no_link_no_mailto_and_untrusted_advice():
    k = kit(mk(trusted=()))
    assert (k.careers_url, k.mailto, k.official_domain, k.trusted) == (None, None, None, False)
    assert k.advice == ADVICE_UNTRUSTED and k.message


def test_trusted_kit_mailto_has_no_recipient_and_encoded_body():
    c = mk("Pay the fee.", company="Infosys Limited", role="Systems Engineer", sender="hr@infosys-careers.in")
    k = kit(c)
    assert k.trusted and k.advice == ADVICE_TRUSTED and k.careers_url == "https://careers.infosys.com/"
    assert k.mailto.startswith("mailto:?subject=")  # no recipient: the student takes it from the official site
    q = parse_qs(urlparse(k.mailto).query)
    assert q["subject"] == ["Verifying a job offer from Infosys Limited"] and q["body"] == [k.message]
    assert " " not in k.mailto


LEAKY = ("Greetings from Infosys Limited. Apply at https://evil-infosys.example/apply or http://bit.ly/zz, "
         "mail hr@infosys-careers.in, call +91 98765 43210, join t.me/scamchan or wa.me/919876543210. "
         "Pay Rs. 500 registration fee to ab@okaxis. Name: Rahul Sharma, Aadhaar [REDACTED].")


def test_no_offer_or_sender_links_leak_into_actionable_fields():
    c = mk(LEAKY, company="Infosys Limited", sender="hr@infosys-careers.in", upi=["ab@okaxis"])
    k = kit(c, flags=["FEE"])
    actionable = " ".join(filter(None, [k.official_domain, k.careers_url, k.advice, unquote(k.mailto.split("?")[0])]))
    for bad in ("evil-infosys", "bit.ly", "infosys-careers", "t.me", "wa.me", "98765"):
        assert bad not in actionable
    assert urlparse(k.careers_url).netloc.endswith("infosys.com")
    # the message quotes only the sender address and UPI ID as plain text: no links, no phone numbers
    assert not re.search(r"https?://|www\.|t\.me|wa\.me|bit\.ly|\d{10}", k.message)
    for personal in ("Rahul", "Sharma", "Aadhaar", "REDACTED", "98765"):
        assert personal not in k.message


def test_pipeline_returns_kit_with_careers_for_a_trusted_company(monkeypatch):
    stub = Stub([page("https://careers.wipro.com/job", "Software Engineer Intern - Wipro")])
    monkeypatch.setattr(pl, "Serp", lambda mode: stub)
    out = asyncio.run(pl.check(CheckRequest(offer_text="Greetings from Wipro Limited. Please reply to confirm. Pay Rs. 500 registration fee to ab@okaxis.",
                                            role="Software Engineer Intern"), "live"))
    k = out.verify_kit
    assert k.trusted and k.official_domain == "wipro.com" and k.mailto and "₹500" in k.message
    assert any(c.id == "official_careers" for c in out.checks)
