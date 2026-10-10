"""Checkpoint C: phrase selection, classification, override, weights. Stubbed search, no network."""
import asyncio
import re

import pytest

import app.pipeline as pl
from app import policy
from app.checks import result, template_trace
from app.extract import extract
from app.fingerprint import select_phrases
from app.models import CheckRequest, Ctx, Identifiers
from app.registry import ORDER, TOTAL_WEIGHT
from app.serp import Hit

OFFER = (
    "Dear Rahul Sharma, congratulations! "
    "You have been shortlisted for the Remote Data Annotation Internship at Zentrix Labs Pvt Ltd. "
    "To confirm your seat you must deposit the refundable onboarding amount and send the receipt on Telegram. "
    "Contact hr@zentrix-labs.in or call +91 98765 43210 before 15 March 2026. "
    "Stipend Rs. 18,000 per month. Best regards."
)


def phrases(text, **kw):
    return select_phrases(text, extract(text, **kw))


# ---- C1: phrase selection ------------------------------------------------------------
def test_strips_personal_and_specific_details():
    out = " ".join(phrases(OFFER, company="Zentrix Labs Pvt Ltd")).lower()
    for bad in ("rahul", "sharma", "zentrix", "98765", "hr@", "march", "18,000", "http"):
        assert bad not in out


def test_phrase_never_spans_a_removed_span():
    # the amount sits between "deposit" and "to": a phrase may not glue them together
    for p in phrases("You must pay Rs. 500 refundable registration fee to confirm your seat for the internship today"):
        assert "pay refundable" not in p.lower()


def test_generic_hr_sentences_are_rejected():
    assert phrases("Dear Candidate, we are pleased to offer you the position. Please find attached your offer letter. "
                   "Thank you for applying and we are looking forward to welcome you to the team. Best regards.") == []


def test_at_most_two_phrases_each_8_to_12_words():
    ph = phrases(OFFER, company="Zentrix Labs Pvt Ltd")
    assert 1 <= len(ph) <= 2
    assert all(8 <= len(p.split()) <= 12 for p in ph)


def test_short_or_stopword_heavy_messages_return_nothing():
    assert phrases("Pay the fee now") == []
    assert phrases("It is what it is and that is all that we can say to you for the time being then") == []


def test_overlapping_second_phrase_is_dropped():
    s = "You are selected for the remote data entry internship role. You are selected for the remote data entry internship role again."
    assert len(phrases(s)) == 1


def test_splitter_keeps_rs_urls_emails_whole():
    from app.checks.text_red_flags import sentences

    got = sentences("Pay Rs. 500 now. Join t.me/abc and mail a@b.co.in. Rate is 3.5 percent.")
    assert got == ["Pay Rs 500 now", "Join t.me/abc and mail a@b.co.in", "Rate is 3.5 percent."]


# ---- C2: classification --------------------------------------------------------------
PHRASE_TEXT = "selected for the remote data annotation internship and must deposit the refundable onboarding amount"


class Stub:
    used = 0
    keys: list = []

    def __init__(self, organic):
        self.organic, self.queries = organic, []

    def search(self, params):
        self.queries.append(params["q"])
        return Hit({"organic_results": self.organic}, "2026-01-01T00:00:00+00:00", False)


def ctx(text=PHRASE_TEXT, company="Zentrix Labs", trusted=()):
    c = Ctx(text, company, None, None, Identifiers(), official=list(trusted), trusted=list(trusted))
    c.extracted = extract(text, company=company)
    return c


def page(domain, title, snippet=""):
    return {"title": title, "link": f"https://{domain}/x", "snippet": snippet}


# a hit must contain the phrase verbatim (the selected phrase is the span from "remote data" on)
MATCH = "selected for the remote data annotation internship and must deposit the refundable onboarding amount today"


def test_fail_on_scam_report():
    r = template_trace.run(ctx(), Stub([page("consumercomplaints.in", MATCH), page("ok.com", "unrelated page")]))
    assert r.status == "fail" and r.phrases and r.evidence[0].kind == "scam_report"
    r = template_trace.run(ctx(), Stub([page("blog.example", "Fake offer alert", MATCH)]))
    assert r.status == "fail"


def test_warn_when_same_text_under_other_names():
    org = [page("a.example", "Hiring at Acme Corp", MATCH), page("b.example", "Join Globex", MATCH)]
    r = template_trace.run(ctx(), Stub(org))
    assert r.status == "warn" and {e.kind for e in r.evidence} == {"reused"}
    assert template_trace.run(ctx(), Stub(org[:1])).status == "unknown"  # one site is not a pattern


def test_pass_only_for_trusted_official_domain():
    org = [page("zentrix.com", "Zentrix Labs careers", MATCH)]
    assert template_trace.run(ctx(trusted=["zentrix.com"]), Stub(org)).status == "pass"
    assert template_trace.run(ctx(), Stub(org)).status == "unknown"  # no trusted domain: can't call it official


def test_unknown_cases_and_weak_matches():
    assert template_trace.run(ctx(), Stub([])).status == "unknown"
    assert template_trace.run(ctx(), Stub([page("a.example", "totally different words here")])).status == "unknown"
    short = ctx("Pay the fee now")
    stub = Stub([])
    r = template_trace.run(short, stub)
    assert r.status == "unknown" and "too short or too generic" in r.finding and stub.queries == []


def test_queries_are_exact_phrases_and_at_most_two():
    stub = Stub([])
    template_trace.run(ctx(OFFER, company="Zentrix Labs Pvt Ltd"), stub)
    assert 1 <= len(stub.queries) <= 2 and all(re.fullmatch(r'"[^"]+"', q) for q in stub.queries)


# ---- C3: policy and weights ----------------------------------------------------------
def R(id, status, w, **kw):
    return result(id, id, w, status, "x", **kw)


def test_total_weight_comes_from_registered_checks():
    assert TOTAL_WEIGHT == sum(m.WEIGHT for m in ORDER) == 120
    assert "template_trace" in {m.ID for m in ORDER}


def test_coverage_correct_when_template_trace_unknown():
    checks = [R("sender_identity", "pass", 30), R("text_red_flags", "pass", 30), R("job_listing", "pass", 10),
              R("template_trace", "unknown", 20)]
    assert policy.decide(checks)["coverage"] == 70 / 120
    checks[3] = R("template_trace", "pass", 20)
    assert policy.decide(checks)["coverage"] == 90 / 120


def test_template_reported_forces_high_risk_but_warn_only_adds_score():
    base = [R("sender_identity", "pass", 30), R("text_red_flags", "pass", 30), R("job_listing", "pass", 10)]
    d = policy.decide(base + [R("template_trace", "fail", 20)])
    assert d["verdict"] == "HIGH_RISK" and "TEMPLATE_REPORTED" in {o.rule for o in d["overrides"]}
    d = policy.decide(base + [R("template_trace", "warn", 20)])
    assert not d["overrides"] and d["risk_score"] == round(100 * 10 / 90)


# ---- end to end through the pipeline ---------------------------------------------------
def test_pipeline_runs_template_trace_and_reports_phrases(monkeypatch):
    stub = Stub([page("consumercomplaints.in", MATCH)])
    stub.used, stub.keys = 0, []
    monkeypatch.setattr(pl, "Serp", lambda mode: stub)
    text = "Greetings from Zentrix Labs. You are selected for the remote data annotation internship and must deposit the refundable onboarding amount today."
    out = asyncio.run(pl.check(CheckRequest(offer_text=text), "live"))
    t = next(c for c in out.checks if c.id == "template_trace")
    assert t.status == "fail" and t.phrases and out.verdict == "HIGH_RISK"
    assert "TEMPLATE_REPORTED" in {o.rule for o in out.overrides}


def test_job_boards_do_not_count_as_reused_wording():
    # found by the real fee-scam run: Internshala/Indeed list "work from home data entry internship" for everyone
    boards = [page("internshala.com", "Data Entry Internships", MATCH), page("in.indeed.com", "Data entry jobs", MATCH),
              page("www.naukri.com", "Data entry", MATCH)]
    assert template_trace.run(ctx(), Stub(boards)).status == "unknown"
    # ...but a scam keyword on a job board is still a scam report
    r = template_trace.run(ctx(), Stub([page("internshala.com", "Beware: fake internship offers", MATCH)]))
    assert r.status == "fail"
    # and non-board sites still count
    two = [page("a.example", "Hiring at Acme", MATCH), page("b.example", "Join Globex", MATCH)] + boards
    assert template_trace.run(ctx(), Stub(two)).status == "warn"


def test_loose_word_overlap_is_not_a_wording_match():
    # found by the real J1 run: Google relaxed the quotes and returned a Reddit thread and a job aggregator that
    # merely share generic words with the phrase. Neither contains the phrase, so neither may count.
    phrase = "Apply after an online assessment and a technical interview"
    text = f"Our company is hiring an Associate Software Engineer in Bengaluru. {phrase}."
    c = ctx(text)
    loose = [page("reddit.com", "Post technical assessment interview : r/SQL", "I had an online assessment and a technical interview"),
             page("ambitionbox.com", "Associate Software Engineer Jobs in Bengaluru", "online assessment technical interview apply")]
    assert template_trace.run(c, Stub(loose)).status == "unknown"
    # a scam keyword on a loosely matching page must not fail the check either (that would force HIGH RISK)
    scammy = [page("reddit.com", "Is this a scam?", "online assessment technical interview apply after")]
    assert template_trace.run(c, Stub(scammy)).status == "unknown"
    # the same pages count once they really contain the phrase (punctuation and case don't matter)
    exact = [page("blog.example", "Fake job scam alert", f"They sent: “{phrase.upper()}!”")]
    assert template_trace.run(c, Stub(exact)).status == "fail"
