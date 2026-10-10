"""Investigate-the-journey: new checks, overrides, timeline rules, safety. Stubbed search, no network."""
import asyncio
import socket

import pytest
from fastapi.testclient import TestClient

import app.pipeline as pl
from app import policy
from app.checks import (interview_process, listing_clone, listing_offer_consistency, listing_source, recruiter_trace,
                        result)
from app.extract import extract
from app.fingerprint import select_phrases
from app.journey import build_ctx, build_timeline, investigate
from app.main import app
from app.models import Ctx, Identifiers, JourneyInput
from app.samples import JOURNEY_SAMPLES, SAMPLES
from app.serp import Hit


class Stub:
    used = 0
    keys: list = []

    def __init__(self, fn=lambda p: {}):
        self.fn, self.queries = fn, []

    def search(self, params):
        self.queries.append(params["q"])
        return Hit(self.fn(params), "2026-01-01T00:00:00+00:00", False)


def page(domain, title, snippet=""):
    return {"title": title, "link": f"https://{domain}/x", "snippet": snippet}


def ctx_for(journey: dict, trusted=("infosys.com",), official=None, company="Infosys Limited", text=""):
    journey = {"offer_text": "placeholder offer text", **journey} if not any(journey.get(k) for k in ("listing", "recruiter", "interview", "offer_text")) else journey
    c = Ctx(text, company, None, None, Identifiers(), official=list(official if official is not None else trusted),
            trusted=list(trusted), journey=JourneyInput(**journey))
    return c


# ---- input model --------------------------------------------------------------------------
def test_input_needs_at_least_one_stage_with_content():
    for bad in ({}, {"company": "Acme", "role": "dev"}, {"offer_text": "  "}, {"listing": {"url": " "}}, {"recruiter": {}}):
        with pytest.raises(ValueError):
            JourneyInput(**bad)
    assert JourneyInput(interview={"asked_to_pay": False}).interview.asked_to_pay is False
    with pytest.raises(ValueError):
        JourneyInput(offer_text="x" * 10_001)
    with pytest.raises(ValueError):
        JourneyInput(listing={"text": "x" * 10_001})


def test_endpoint_returns_422_for_empty_and_200_for_a_stage():
    c = TestClient(app)
    assert c.post("/api/investigate?mode=cached", json={}).status_code == 422
    r = c.post("/api/investigate?mode=cached", json={"interview": {"asked_to_pay": True}})
    assert r.status_code == 200
    j = r.json()
    assert j["verdict"] == "HIGH_RISK" and len(j["timeline"]) == 5 and "meta" not in j["checks"][0]


# ---- company resolution order -------------------------------------------------------------
def test_company_resolution_order():
    full = dict(company="Typed Co", offer_text="Greetings from Offer Co. Join us.", listing={"text": "Hiring at Listing Co now"},
                recruiter={"email": "x@emaildomain.com"})
    assert build_ctx(JourneyInput(**full)).company == "Typed Co"
    full.pop("company")
    assert build_ctx(JourneyInput(**full)).company == "Offer Co"
    full.pop("offer_text"); full["offer_text"] = "Please reply to confirm your seat."
    assert build_ctx(JourneyInput(**full)).company == "Listing Co"
    assert build_ctx(JourneyInput(recruiter={"email": "x@emaildomain.com"})).company == "Emaildomain"
    assert build_ctx(JourneyInput(recruiter={"email": "x@gmail.com"})).company is None      # free mail says nothing
    assert build_ctx(JourneyInput(recruiter={"email": "x@jobs.lever.co"})).company is None  # nor does a hiring platform


def test_recruiter_contact_feeds_the_existing_identifier_checks():
    ctx = build_ctx(JourneyInput(recruiter={"email": "HR@Acme.example", "phone": "+91 98765 43210"}, offer_text="Join us today please"))
    assert ctx.sender_email == "hr@acme.example"
    assert "9876543210" in ctx.identifiers.phones and "hr@acme.example" in ctx.identifiers.emails


# ---- 2a listing_source --------------------------------------------------------------------
@pytest.mark.parametrize("url,status", [
    ("https://www.infosys.com/careers/job1", "pass"),
    ("https://career.infosys.com/x", "pass"),
    ("https://www.naukri.com/job-listings-x", "info"),
    ("https://in.indeed.com/viewjob?jk=1", "info"),
    ("https://careers-infosys.in/jobs", "fail"),
    ("https://infosys.com.evil.example/jobs", "fail"),
    ("https://randomjobs.example/x", "warn"),
    ("randomjobs.example/x", "warn"),
])
def test_listing_source_rules(url, status):
    assert listing_source.run(ctx_for({"listing": {"url": url}})).status == status


def test_listing_source_unknowns_and_untrusted():
    assert listing_source.run(ctx_for({"listing": {"text": "only text"}})).status == "unknown"
    assert listing_source.run(ctx_for({"listing": {"url": "not a url"}})).status == "unknown"
    # no confirmed official site: can't say the listing is "not the company's"
    assert listing_source.run(ctx_for({"listing": {"url": "https://randomjobs.example/x"}}, trusted=(), official=())).status == "unknown"
    # matches only the top search result: a warning, never a pass
    r = listing_source.run(ctx_for({"listing": {"url": "https://acme.example/jobs"}}, trusted=(), official=("acme.example",)))
    assert r.status == "warn" and "couldn't confirm" in r.finding


# ---- 2b listing_clone ---------------------------------------------------------------------
LISTING = "We are hiring an Associate Software Engineer to build and maintain internal web applications for enterprise customers"


def _hit_for(text, company="Infosys Limited", **page_kw):
    ph = select_phrases(text, extract(text, company=company))
    assert ph, "test text must yield a phrase"
    return ph[0]


def test_listing_clone_no_text_is_unknown_and_makes_no_search():
    stub = Stub()
    assert listing_clone.run(ctx_for({"listing": {"url": "https://x.example"}}), stub).status == "unknown" and not stub.queries


def test_listing_clone_scam_report_fails_and_other_company_warns():
    c = ctx_for({"listing": {"text": LISTING}})
    phrase = _hit_for(LISTING)
    r = listing_clone.run(c, Stub(lambda p: {"organic_results": [page("complaints.example", "Fake job scam alert", phrase)]}))
    assert r.status == "fail"
    one = [page("jobs.example", "Associate Software Engineer at Globex Industries", phrase)]
    r = listing_clone.run(c, Stub(lambda p: {"organic_results": one}))
    assert r.status == "warn" and "another company's name" in r.finding and r.evidence[0].kind == "reused"


def test_listing_clone_single_unnamed_reuse_and_job_boards_are_unknown_official_passes():
    c = ctx_for({"listing": {"text": LISTING}})
    phrase = _hit_for(LISTING)
    unnamed = [page("blog.example", "Interesting careers post", phrase)]
    assert listing_clone.run(c, Stub(lambda p: {"organic_results": unnamed})).status == "unknown"
    board = [page("internshala.com", "Software Engineer at Globex Industries", phrase)]
    assert listing_clone.run(c, Stub(lambda p: {"organic_results": board})).status == "unknown"
    off = [page("www.infosys.com", "Infosys careers", phrase)]
    assert listing_clone.run(c, Stub(lambda p: {"organic_results": off})).status == "pass"


def test_listing_clone_flags_a_fee_in_the_listing():
    text = "Pay Rs. 500 registration fee to apply for the Associate Software Engineer role at our company in Bengaluru today"
    r = listing_clone.run(ctx_for({"listing": {"text": text}}), Stub())
    assert "FEE" in r.flags


# ---- 2c recruiter_trace -------------------------------------------------------------------
def test_recruiter_trace_needs_name_and_company_and_never_passes_or_fails():
    stub = Stub()
    assert recruiter_trace.run(ctx_for({"recruiter": {"email": "a@b.example"}}), stub).status == "unknown" and not stub.queries
    assert recruiter_trace.run(ctx_for({"recruiter": {"name": "Asha Rao"}}, company=None), stub).status == "unknown" and not stub.queries

    stub = Stub(lambda p: {"organic_results": [page("in.linkedin.com", "Asha Rao - Talent Partner - Infosys | LinkedIn", "private details")]})
    r = recruiter_trace.run(ctx_for({"recruiter": {"name": "Asha Rao"}}), stub)
    assert stub.queries == ['site:linkedin.com/in "Asha Rao" "Infosys Limited"']
    assert r.status == "info" and "can be faked" in r.finding
    assert [(e.title, e.snippet) for e in r.evidence] == [("Asha Rao - Talent Partner - Infosys | LinkedIn", "")]  # title and link only
    other = Stub(lambda p: {"organic_results": [page("linkedin.com", "Asha Rao - Globex")]})
    r = recruiter_trace.run(ctx_for({"recruiter": {"name": "Asha Rao"}}), other)
    assert r.status == "unknown" and r.status not in ("pass", "fail") and r.weight == 0


# ---- 2d interview_process -----------------------------------------------------------------
@pytest.mark.parametrize("fmt,status,flag", [
    ("none", "fail", "NO_REAL_INTERVIEW"), ("chat_only", "fail", "NO_REAL_INTERVIEW"),
    ("phone", "pass", None), ("other_video", "pass", None), ("official_portal_or_video", "pass", None),
])
def test_interview_formats(fmt, status, flag):
    r = interview_process.run(ctx_for({"interview": {"format": fmt}}, trusted=()), Stub())
    assert r.status == status and (flag in r.flags if flag else "NO_REAL_INTERVIEW" not in r.flags)


def test_interview_documents_before_offer_is_at_least_a_warning():
    r = interview_process.run(ctx_for({"interview": {"format": "phone", "asked_for_documents_before_offer": True}}, trusted=()), Stub())
    assert r.status == "warn" and "DOCS_BEFORE_OFFER" in r.flags and "Aadhaar, PAN or bank details" in r.finding
    r = interview_process.run(ctx_for({"interview": {"format": "chat_only", "asked_for_documents_before_offer": True}}, trusted=()), Stub())
    assert r.status == "fail"  # never softened


def test_interview_payment_is_carried_as_a_flag_for_the_override_not_scored_here():
    r = interview_process.run(ctx_for({"interview": {"format": "phone", "asked_to_pay": True}}, trusted=()), Stub())
    assert r.status == "pass" and "ASKED_TO_PAY" in r.flags and r.meta["asked_to_pay"]
    r = interview_process.run(ctx_for({"interview": {"asked_to_pay": True}}, trusted=()), Stub())
    assert r.status == "unknown" and r.meta["asked_to_pay"]


def test_interview_no_details_is_unknown_without_a_search():
    stub = Stub()
    r = interview_process.run(ctx_for({"offer_text": "some offer text here"}), stub)
    assert r.status == "unknown" and not stub.queries


def test_interview_official_process_link_only_for_a_trusted_domain():
    org = [page("evil.example", "Fake process"), page("www.infosys.com", "Our hiring process", "How we select")]
    stub = Stub(lambda p: {"organic_results": org})
    r = interview_process.run(ctx_for({"interview": {"format": "phone"}}), stub)
    assert stub.queries == ["site:infosys.com recruitment process OR hiring process OR selection process"]
    assert r.meta["official_process_url"] == "https://www.infosys.com/x" and "Compare with the company's published hiring process." in r.finding
    stub = Stub()
    interview_process.run(ctx_for({"interview": {"format": "phone"}}, trusted=(), official=("guess.example",)), stub)
    assert stub.queries == []  # untrusted domain: no search, no link
    nothing = interview_process.run(ctx_for({"interview": {"format": "phone"}}), Stub())
    assert nothing.evidence == [] and "Compare with" not in nothing.finding


def test_interview_result_does_not_depend_on_the_search():
    class Boom(Stub):
        def search(self, params):
            raise RuntimeError("search down")

    assert interview_process.run(ctx_for({"interview": {"format": "chat_only"}}), Boom()).status == "fail"


# ---- 2e listing_offer_consistency -----------------------------------------------------------
def consistency(listing, offer):
    return listing_offer_consistency.run(ctx_for({"listing": {"text": listing}, "offer_text": offer}))


def test_company_mismatch_fails():
    r = consistency("Software Engineer position at Acme Robotics in Pune. Stipend ₹20,000 per month.",
                    "Greetings from Globex Industries. We offer Software Engineer in Pune, stipend ₹20,000 per month.")
    assert r.status == "fail" and "COMPANY_MISMATCH" in r.flags
    assert "Listing said the company is Acme Robotics, offer says Globex Industries." in r.finding


def test_company_names_that_share_a_token_or_substring_agree():
    r = consistency("Software Engineer position at Infosys in Pune. Stipend ₹20,000 per month.",
                    "Greetings from Infosys Limited. Software Engineer in Pune, stipend ₹20,000 per month.")
    assert r.status == "pass"


def test_role_pay_and_city_differences_warn_and_list_both_values():
    r = consistency("Greetings from Infosys. Associate Software Engineer in Bengaluru. Stipend ₹20,000 per month.",
                    "Greetings from Infosys. You are selected as Data Entry Executive in Noida. Stipend ₹40,000 per month.")
    assert r.status == "warn" and "COMPANY_MISMATCH" not in r.flags
    assert "Listing said pay is ₹20,000 per month, offer says ₹40,000 per month." in r.finding
    assert "Listing said the location is Bengaluru, offer says Noida." in r.finding
    assert "Listing said the role is" in r.finding


def test_pay_within_25_percent_and_everything_agreeing_pass():
    r = consistency("Systems Engineer in Pune. Stipend ₹30,000 per month.", "Systems Engineer in Pune. Stipend ₹35,000 per month.")
    assert r.status == "pass"
    assert consistency("CTC 6 LPA, Systems Engineer", "Systems Engineer offer, salary ₹50,000 per month").status in ("pass", "unknown")


def test_too_little_to_compare_or_a_missing_text_is_unknown():
    assert consistency("We are hiring.", "We offer a role.").status == "unknown"
    assert listing_offer_consistency.run(ctx_for({"offer_text": "only an offer here"})).status == "unknown"


# ---- overrides ----------------------------------------------------------------------------
def R(id, status, w, **kw):
    return result(id, id, w, status, "x", **kw)


def test_payment_in_process_from_the_interview_answer_or_any_stage_text():
    base = [R("sender_identity", "pass", 30), R("text_red_flags", "pass", 30)]
    d = policy.decide(base + [R("interview_process", "pass", 15, asked_to_pay=True)])
    assert d["verdict"] == "HIGH_RISK" and "PAYMENT_IN_PROCESS" in {o.rule for o in d["overrides"]}
    d = policy.decide(base + [R("interview_process", "pass", 15), R("listing_clone", "unknown", 15, flags=["FEE"])])
    assert "PAYMENT_IN_PROCESS" in {o.rule for o in d["overrides"]}
    d = policy.decide(base + [R("interview_process", "pass", 15)])
    assert "PAYMENT_IN_PROCESS" not in {o.rule for o in d["overrides"]}


def test_journey_overrides_are_inert_without_the_journey_checks():
    quick = [R("sender_identity", "pass", 30), R("text_red_flags", "fail", 30, flags=["FEE"])]
    assert "PAYMENT_IN_PROCESS" not in {o.rule for o in policy.decide(quick)["overrides"]}


def test_company_mismatch_no_real_interview_lookalike_listing_and_never_lower():
    base = [R("sender_identity", "pass", 30), R("text_red_flags", "pass", 30), R("job_listing", "pass", 10)]
    d = policy.decide(base + [R("listing_offer_consistency", "fail", 15, flags=["COMPANY_MISMATCH"])])
    assert d["verdict"] == "HIGH_RISK" and "COMPANY_MISMATCH" in {o.rule for o in d["overrides"]}
    d = policy.decide(base + [R("interview_process", "fail", 15, flags=["NO_REAL_INTERVIEW"])])
    assert "NO_REAL_INTERVIEW" in {o.rule for o in d["overrides"]}
    assert d["verdict"] in ("CAUTION", "HIGH_RISK")
    d = policy.decide(base + [R("listing_source", "fail", 10)])
    assert d["verdict"] == "HIGH_RISK" and "LOOKALIKE_LISTING" in {o.rule for o in d["overrides"]}
    d = policy.decide(base + [R("interview_process", "fail", 15, flags=["NO_REAL_INTERVIEW"], asked_to_pay=True)])
    assert d["verdict"] == "HIGH_RISK"  # the CAUTION override can't lower the payment one


# ---- timeline -----------------------------------------------------------------------------
IDS = ["listing_source", "listing_clone", "sender_identity", "identifier_trace", "recruiter_trace", "interview_process",
       "text_red_flags", "template_trace", "listing_offer_consistency", "job_listing", "registration", "official_careers"]


def results(**over):
    base = {i: result(i, i, 10, "unknown", "unknown finding.") for i in IDS}
    base.update(over)
    return base


def node(tl, stage):
    return next(n for n in tl if n.stage == stage)


def test_stage_without_input_is_not_provided_and_five_nodes_in_order():
    tl, first = build_timeline(JourneyInput(offer_text="Please confirm your seat today."), results(), [])
    assert [n.stage for n in tl] == ["listing", "recruiter", "interview", "payment", "offer"]
    assert [n.status for n in tl][:3] == ["not_provided"] * 3
    assert node(tl, "payment").status == "unverified" and node(tl, "offer").status == "unverified" and first is None
    tl, _ = build_timeline(JourneyInput(interview={"format": "phone"}), results(), [])
    assert node(tl, "payment").status == "not_provided"  # no payment answer and no text at all


def test_stage_status_rules():
    j = JourneyInput(listing={"url": "https://x.example"}, offer_text="offer text here please")
    tl, _ = build_timeline(j, results(listing_source=R("listing_source", "pass", 10), text_red_flags=R("text_red_flags", "warn", 30)), [])
    assert node(tl, "listing").status == "matches" and node(tl, "offer").status == "diverges"
    tl, _ = build_timeline(j, results(listing_source=R("listing_source", "info", 10)), [])
    assert node(tl, "listing").status == "unverified"  # info and unknown never make a stage "match"
    tl, _ = build_timeline(j, results(listing_source=R("listing_source", "pass", 10), listing_clone=R("listing_clone", "fail", 15)), [])
    assert node(tl, "listing").status == "diverges"


def test_job_listing_and_registry_warnings_do_not_make_the_offer_stage_diverge():
    j = JourneyInput(offer_text="Please confirm your seat today.")
    tl, first = build_timeline(j, results(text_red_flags=R("text_red_flags", "pass", 30), job_listing=R("job_listing", "warn", 10),
                                          registration=R("registration", "warn", 5)), [])
    assert node(tl, "offer").status == "matches" and first is None
    assert {"job_listing", "registration"} <= set(node(tl, "offer").check_ids)  # still shown


def test_first_divergence_follows_journey_order_and_uses_the_strongest_finding():
    j = JourneyInput(recruiter={"email": "a@b.example"}, offer_text="Offer text goes here now")
    res = results(sender_identity=result("sender_identity", "s", 30, "warn", "Weak sender note. More."),
                  identifier_trace=result("identifier_trace", "i", 25, "fail", "Number reported as a scam. Extra."),
                  text_red_flags=R("text_red_flags", "fail", 30))
    tl, first = build_timeline(j, res, [])
    assert first.stage == "recruiter" and first.reason == "Number reported as a scam."  # fail beats warn; first sentence only
    res = results(sender_identity=result("sender_identity", "s", 30, "warn", "Heavier warning."),
                  identifier_trace=result("identifier_trace", "i", 25, "warn", "Lighter warning."))
    assert build_timeline(j, res, [])[1].reason == "Heavier warning."  # same rank: higher weight wins


def test_recruiter_channel_rule():
    j = JourneyInput(recruiter={"channel": "telegram"})
    tl, first = build_timeline(j, results(), [])
    assert node(tl, "recruiter").status == "diverges" and "Telegram" in first.reason
    ok = results(sender_identity=R("sender_identity", "pass", 30))
    assert node(build_timeline(j, ok, [])[0], "recruiter").status == "matches"
    assert node(build_timeline(JourneyInput(recruiter={"channel": "email"}), results(), [])[0], "recruiter").status == "unverified"


def test_payment_stage_rules():
    from app.models import Override

    paid = [Override(rule="PAYMENT_IN_PROCESS", reason="r", verdict="HIGH_RISK")]
    tl, first = build_timeline(JourneyInput(interview={"asked_to_pay": True}), results(), paid)
    assert node(tl, "payment").status == "diverges" and first.stage == "payment"
    tl, _ = build_timeline(JourneyInput(offer_text="Offer text goes here now", interview={"asked_to_pay": False}), results(), [])
    assert node(tl, "payment").status == "matches"
    tl, _ = build_timeline(JourneyInput(offer_text="Pay a fee please now today"), results(), paid)  # from a FEE flag, not an answer
    assert node(tl, "payment").status == "diverges" and "demands a payment" in node(tl, "payment").headline


# ---- end to end -----------------------------------------------------------------------------
def run(journey, monkeypatch, fn=lambda p: {}):
    stub = Stub(fn)
    monkeypatch.setattr(pl, "Serp", lambda mode: stub)
    return asyncio.run(investigate(JourneyInput(**journey), "live")), stub


def test_asked_to_pay_forces_high_risk_from_any_stage(monkeypatch):
    out, _ = run({"interview": {"asked_to_pay": True}}, monkeypatch)
    assert out.verdict == "HIGH_RISK" and out.first_divergence.stage == "payment"
    out, _ = run({"recruiter": {"email": "hr@infosys.com"}, "interview": {"format": "official_portal_or_video", "asked_to_pay": True}}, monkeypatch)
    assert out.verdict == "HIGH_RISK"
    out, _ = run({"listing": {"text": "Pay Rs. 500 registration fee to apply for this role at our company today please"}}, monkeypatch)
    assert out.verdict == "HIGH_RISK" and "PAYMENT_IN_PROCESS" in {o.rule for o in out.overrides}


def test_pii_in_every_stage_is_redacted_before_any_search(monkeypatch):
    out, stub = run({"listing": {"text": "Aadhaar 1234 5678 9012 hiring Associate Software Engineer at Infosys in Pune for everyone"},
                     "offer_text": "Greetings from Infosys. Send PAN ABCDE1234F and Aadhaar 1234 5678 9012 to confirm your seat today please",
                     "recruiter": {"name": "Asha Rao", "email": "asha@infosys.example"}}, monkeypatch)
    assert stub.queries and not any(("1234 5678" in q or "ABCDE1234F" in q) for q in stub.queries)
    assert set(out.redacted) == {"aadhaar", "pan"}


def test_the_listing_url_is_never_fetched(monkeypatch):
    import httpx
    import requests

    calls = []  # a check swallows its own exceptions, so raising alone would hide a fetch: record it too

    def boom(*a, **k):
        calls.append(a)
        raise AssertionError("an HTTP request was made")

    for target in (requests.sessions.Session, "request"), (httpx.Client, "send"), (httpx.AsyncClient, "send"):
        monkeypatch.setattr(target[0], target[1], boom)
    monkeypatch.setattr("urllib.request.urlopen", boom)
    stub = Stub()
    monkeypatch.setattr(pl, "Serp", lambda mode: stub)

    async def go():
        # the loop already exists, so blocking new connections now only affects what the code under test does
        monkeypatch.setattr(socket.socket, "connect", boom)
        return await investigate(JourneyInput(listing={"url": "https://evil-listing.example/jobs?x=1", "text": "Hiring now at Acme in Pune"},
                                              offer_text="Greetings from Acme. Please confirm your seat today."), "live")

    out = asyncio.run(go())
    assert not calls, "something tried to reach the network"
    assert out.timeline and all("evil-listing" not in q for q in stub.queries)  # only its domain is ever judged, as text


# ---- acceptance (cached mode, recorded fixtures only) ------------------------------------------
def cached(name):
    return asyncio.run(investigate(JourneyInput(**JOURNEY_SAMPLES[name]["journey"]), "cached"))


def test_j1_cloned_listing_is_high_risk_with_first_divergence_at_the_listing():
    out = cached("J1_CLONED_LISTING")
    rules = {o.rule for o in out.overrides}
    assert out.verdict == "HIGH_RISK" and out.first_divergence.stage == "listing"
    assert {"LOOKALIKE_LISTING", "PAYMENT_IN_PROCESS", "NO_REAL_INTERVIEW"} <= rules
    assert [n.status for n in out.timeline] == ["diverges"] * 5


def test_j2_genuine_journey_is_not_high_risk_with_no_divergence():
    out = cached("J2_GENUINE_JOURNEY")
    assert out.verdict != "HIGH_RISK" and out.first_divergence is None
    assert all(n.status == "matches" for n in out.timeline)


def test_samples_endpoint_serves_both_kinds_and_quick_samples_are_untouched():
    data = TestClient(app).get("/api/samples").json()
    assert {k for k, v in data.items() if v["kind"] == "journey"} == set(JOURNEY_SAMPLES)
    assert {k for k, v in data.items() if v["kind"] == "quick"} == set(SAMPLES)
    assert not set(SAMPLES) & set(JOURNEY_SAMPLES) and all("kind" not in v for v in SAMPLES.values())


def test_quick_check_endpoint_is_unchanged():
    c = TestClient(app)
    j = c.post("/api/check?mode=cached", json={"offer_text": SAMPLES["SCAM_FEE"]["offer_text"]}).json()
    assert "timeline" not in j and "first_divergence" not in j
    assert j["verdict"] == "HIGH_RISK" and "PAYMENT_IN_PROCESS" not in {o["rule"] for o in j["overrides"]}
    assert sum(1 for c_ in j["checks"] if c_["weight"] > 0) == 6 and not any(c_["id"].startswith(("listing", "interview", "recruiter")) for c_ in j["checks"])
