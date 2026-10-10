import asyncio

import pytest

from app import policy, privacy
from app.checks import identifier_trace, result, sender_identity, text_red_flags
from app.checks.sender_identity import classify, is_lookalike, registrable
from app.extract import extract
from app.models import CheckRequest, Ctx, Identifiers
from app.pipeline import check
from app.serp import CacheMiss, Hit


def flags(text):
    return text_red_flags.detect(text)


# ---- text red flags -------------------------------------------------------
def test_negated_fee_not_flagged():
    assert "FEE" not in flags("We never charge any registration fee at any stage of hiring.")
    assert "FEE" not in flags("There is no processing fee for candidates.")


def test_stipend_paid_not_fee():
    assert "FEE" not in flags("Your stipend will be paid monthly. Payroll is handled by HR; see the pay scale.")


def test_hinglish_fee():
    assert "FEE" in flags("500 rupees registration charge jama karo")


def test_negation_does_not_cross_clause():
    assert "FEE" in flags("No interview needed, just pay Rs. 500 today")


def test_upi_is_fee_but_corporate_email_is_not():
    assert "FEE" in flags("send money to abc@okaxis")
    assert "FEE" not in flags("write to hr@sbi.co.in for queries")


def test_flag_counts():
    assert text_red_flags.run(Ctx("Join t.me/x", None, None, None, Identifiers())).status == "warn"
    assert text_red_flags.run(Ctx("Join t.me/x within 24 hours", None, None, None, Identifiers())).status == "fail"
    assert text_red_flags.run(Ctx("Please reply to confirm.", None, None, None, Identifiers())).status == "pass"


# ---- privacy --------------------------------------------------------------
def test_aadhaar_pan_redacted_but_wa_phone_kept():
    t, kinds = privacy.redact("Aadhaar 1234 5678 9012 PAN ABCDE1234F wa.me/919876543210")
    assert "1234" not in t and "ABCDE" not in t and "wa.me/919876543210" in t
    assert kinds == ["aadhaar", "pan"]


# ---- extraction -----------------------------------------------------------
def test_extract_basics():
    e = extract("Greetings from Infosys Limited. Mail hr@infosys.com or pay ab@okaxis, +91 98765 43210, t.me/abcd")
    assert e.company == "Infosys Limited" and e.sender_email == "hr@infosys.com"
    assert e.identifiers.upi == ["ab@okaxis"] and e.identifiers.phones == ["9876543210"] and e.identifiers.telegram == ["abcd"]


def test_sender_skips_dear_line():
    assert extract("Dear student@college.edu\nWrite to hr@acme.com").sender_email == "hr@acme.com"


# ---- sender identity ------------------------------------------------------
def test_lookalike_cases():
    assert is_lookalike("tcs-careers-india.in", "tcs.com")
    assert is_lookalike("infosysrecruitment.com", "infosys.com")
    assert is_lookalike("infosis.com", "infosys.com")
    assert not is_lookalike("hcl.com", "tcs.com")  # short labels never fuzzy-match
    assert not is_lookalike("mail.tcs.com", "tcs.com")


def test_classify():
    assert classify("hr@tcs.com", ["tcs.com"])[0] == "pass"
    assert classify("hr@mail.tcs.com", ["tcs.com"])[0] == "pass"
    assert classify("x@gmail.com", ["tcs.com"])[0] == "fail"
    assert classify("x@jobs.lever.co", ["tcs.com"])[0] == "warn"
    assert classify("x@randomco.com", ["tcs.com"])[0] == "warn"
    assert classify("x@tcs-careers.in", ["tcs.com"])[2]["lookalike"]
    assert registrable("a.b.co.in") == "b.co.in"


# ---- policy ---------------------------------------------------------------
def R(id, status, w, **kw):
    return result(id, id, w, status, "x", **kw)


def test_unknown_and_info_excluded_from_score():
    d = policy.decide([R("sender_identity", "pass", 30), R("text_red_flags", "pass", 30), R("a", "unknown", 25), R("b", "info", 0)])
    assert d["risk_score"] == 0 and d["coverage"] == 0.6


def test_low_coverage_is_not_enough_evidence():
    d = policy.decide([R("text_red_flags", "pass", 30), R("job_listing", "pass", 10)])
    assert d["verdict"] == "NOT_ENOUGH_EVIDENCE"


def test_overrides_only_raise():
    checks = [R("sender_identity", "pass", 30), R("text_red_flags", "pass", 30), R("job_listing", "pass", 10)]
    assert policy.decide(checks)["verdict"] == "NO_RED_FLAGS"
    checks = [R("sender_identity", "fail", 30, free_mail=True), R("text_red_flags", "fail", 30, ), R("identifier_trace", "fail", 25)]
    checks[1] = result("text_red_flags", "t", 30, "fail", "x", flags=["FEE"])
    d = policy.decide(checks)
    assert d["verdict"] == "HIGH_RISK" and {o.rule for o in d["overrides"]} >= {"FEE_DEMANDED", "FREE_MAIL_SENDER", "IDENTIFIER_REPORTED"}


def test_free_mail_is_caution_at_least_and_high_with_notice():
    base = [R("sender_identity", "fail", 30, free_mail=True), R("text_red_flags", "pass", 30), R("job_listing", "pass", 10)]
    assert policy.decide(base)["verdict"] in ("CAUTION", "HIGH_RISK")
    base.append(R("company_fraud_notice", "info", 0, notice_found=True))
    assert policy.decide(base)["verdict"] == "HIGH_RISK"


def test_never_says_safe():
    assert all("safe" not in l.lower().replace("still", "") or "evidence" in l.lower() for l in policy.LABELS.values())


# ---- identifier trace + pipeline with stubbed search ------------------------
class Stub:
    used = 0

    def __init__(self, fn):
        self.fn, self.queries = fn, []

    def search(self, params):
        self.queries.append(params["q"])
        return Hit(self.fn(params), "2026-01-01T00:00:00+00:00", False)


def test_identifier_reported_scam():
    ctx = Ctx("", "Acme", None, None, Identifiers(upi=["x@okaxis"]))
    stub = Stub(lambda p: {"organic_results": [{"title": "x@okaxis is a scam", "link": "https://e.com", "snippet": ""}]})
    assert identifier_trace.run(ctx, stub).status == "fail"
    stub = Stub(lambda p: {"organic_results": [{"title": "Unrelated", "link": "https://e.com", "snippet": "scam news"}]})
    assert identifier_trace.run(ctx, stub).status == "unknown"


def test_search_failure_and_timeout_become_unknown(monkeypatch):
    import app.pipeline as pl

    class Boom:
        used = 0
        keys = []

        def search(self, params):
            raise RuntimeError("boom")

    monkeypatch.setattr(pl, "Serp", lambda mode: Boom())
    out = asyncio.run(check(CheckRequest(offer_text="Hello from Zzyzx Corp. Reply to hr@zzyzx.example to accept."), "live"))
    by = {c.id: c for c in out.checks}
    assert by["job_listing"].status == "unknown" and by["registration"].status == "unknown"
    assert out.verdict == "NOT_ENOUGH_EVIDENCE"

    monkeypatch.setattr(pl, "CHECK_TIMEOUT", 0.05)

    class Slow(Boom):
        def search(self, params):
            import time; time.sleep(0.3)

    monkeypatch.setattr(pl, "Serp", lambda mode: Slow())
    out = asyncio.run(check(CheckRequest(offer_text="Greetings from Zzyzx Corp. Reply to confirm please."), "live"))
    assert next(c for c in out.checks if c.id == "registration").status == "unknown"


def test_aadhaar_never_in_outgoing_query(monkeypatch):
    import app.pipeline as pl

    stub = Stub(lambda p: {})
    stub.keys = []
    monkeypatch.setattr(pl, "Serp", lambda mode: stub)
    asyncio.run(check(CheckRequest(offer_text="Greetings from Acme Corp. Send Aadhaar 1234 5678 9012 and PAN ABCDE1234F to a@okaxis"), "live"))
    assert stub.queries and not any("1234 5678" in q or "ABCDE1234F" in q for q in stub.queries)


def test_third_party_sender_for_known_brand_is_caution():
    assert classify("v@programs-partner.example", ["wipro.com"])[2]["third_party"]
    meta = dict(third_party=True, known_brand=True, company="Wipro", sender_domain="programs-partner.example")
    checks = [R("sender_identity", "warn", 30, **meta), R("text_red_flags", "pass", 30), R("job_listing", "pass", 10)]
    d = policy.decide(checks)
    assert d["verdict"] == "CAUTION" and d["overrides"][0].rule == "THIRD_PARTY_SENDER"
    meta["known_brand"] = False  # unknown company: can't say the domain isn't theirs
    checks[0] = R("sender_identity", "warn", 30, **meta)
    assert not policy.decide(checks)["overrides"]
    assert "third_party" not in classify("x@jobs.lever.co", ["wipro.com"])[2]  # hiring platforms are exempt


def test_job_listing_needs_role_match_not_just_company():
    from app.checks import job_listing

    jobs = {"jobs_results": [{"title": "SOC Analyst", "company_name": "Wipro Limited", "location": "Pune"},
                             {"title": "Software Engineer", "company_name": "Wipro Limited", "location": "Pune"}]}
    run = lambda role: job_listing.run(Ctx("", "Wipro", role, None, Identifiers()), Stub(lambda p: jobs))
    assert run("Software Engineering Internship").status == "pass"   # engineer ~ engineering
    assert run("Marketing Intern").status == "warn"                  # company matches, role doesn't
    assert run("Internship").status == "warn"                        # vague role can't confirm anything
    assert run(None).status == "warn"


WIPRO_STYLE = """Become eligible for performance-based stipend opportunities of up to ₹25,000, subject to applicable criteria.
Month 1-2: Industry Training & Mentorship. Month 3: Stipend-Based Internship.
Please review the eligibility criteria, applicable fees, stipend terms and other guidelines."""


def test_soft_flags_warn_but_never_fail():
    f = flags(WIPRO_STYLE)
    assert {"FEES_UNSTATED", "TRAINING_FIRST"} <= set(f) and "FEE" not in f
    assert text_red_flags.run(Ctx(WIPRO_STYLE, None, None, None, Identifiers())).status == "warn"


def test_soft_flags_dont_fire_on_ordinary_offers_or_when_negated():
    assert not flags("Your 6-month Software Internship has a stipend of ₹30,000 per month after campus interviews.")
    assert "FEES_UNSTATED" not in flags("There are no applicable fees for candidates.")
    assert "TRAINING_FIRST" not in flags("We do not offer a performance-based stipend. Training phase is 2 weeks.")




# ---- checkpoint A: only a trusted official domain can pass -------------------------
def test_untrusted_match_warns_never_passes():
    status, reason, meta = classify("hr@nexora202.online", ["nexora202.online"], trusted=[])
    assert status == "warn" and meta == {"untrusted_match": True}
    assert "couldn't confirm that site is official" in reason
    assert classify("x@mail.nexora202.online", ["nexora202.online"], trusted=[])[0] == "warn"


def test_trusted_matches_pass():
    assert classify("hr@acme.example", ["acme.example"], trusted=["acme.example"])[0] == "pass"   # knowledge panel
    assert classify("hr@wipro.com", ["wipro.com"], trusted=["wipro.com"])[0] == "pass"             # seed list
    assert classify("hr@zohocorp.com", ["zoho.com", "zohocorp.com"], trusted=["zoho.com", "zohocorp.com"])[0] == "pass"


def test_other_branches_unchanged_with_untrusted_official():
    assert classify("x@gmail.com", ["nexora202.online"], trusted=[])[0] == "fail"
    assert classify("x@nexora202-careers.in", ["nexora202.online"], trusted=[])[2].get("lookalike")


def _run_sender(monkeypatch, search, company, sender):
    import app.pipeline as pl
    from app.checks import sender_identity as si

    ctx = Ctx("", company, None, sender, Identifiers())
    return si.run(ctx, Stub(search))


def test_sender_check_end_to_end_trust(monkeypatch):
    organic = {"organic_results": [{"title": "Nexora", "link": "https://nexora202.online/", "snippet": ""}]}
    r = _run_sender(monkeypatch, lambda p: organic, "Nexora Labs", "hr@nexora202.online")
    assert r.status == "warn" and not r.meta["trusted"]
    kg = {"knowledge_graph": {"website": "https://www.nexora.example/"}}
    r = _run_sender(monkeypatch, lambda p: kg, "Nexora Labs", "hr@nexora.example")
    assert r.status == "pass" and r.meta["trusted"] == ["nexora.example"]
    r = _run_sender(monkeypatch, lambda p: {}, "Wipro Limited", "hr@wipro.com")
    assert r.status == "pass"


def test_ctx_exposes_official_domain_trust():
    c = Ctx("", "X", None, None, Identifiers(), official=["guess.com", "real.com"], trusted=["real.com"])
    assert c.official_domain == "real.com" and c.official_domain_trusted
    c = Ctx("", "X", None, None, Identifiers(), official=["guess.com"])
    assert c.official_domain == "guess.com" and not c.official_domain_trusted
    assert Ctx("", "X", None, None, Identifiers()).official_domain is None
