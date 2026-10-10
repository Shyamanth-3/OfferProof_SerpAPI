"""Real-world cases that once slipped through. Search is stubbed, no network."""
import asyncio

import pytest

import app.pipeline as pl
from app.models import CheckRequest
from app.serp import Hit


class Stub:
    used = 0
    keys: list = []

    def __init__(self, fn):
        self.fn = fn

    def search(self, params):
        return Hit(self.fn(params), "2026-01-01T00:00:00+00:00", False)


def run(text, fn, monkeypatch, **kw):
    monkeypatch.setattr(pl, "Serp", lambda mode: Stub(fn))
    return asyncio.run(pl.check(CheckRequest(offer_text=text, **kw), "live"))


# ---- next_steps must not send students to a possibly-fake site ----------------------
FEE = "Greetings from Nexora Global Solutions. Pay Rs. 500 registration fee to ab@okaxis to join."
ORGANIC = {"organic_results": [{"title": "Nexora", "link": "https://nexora202.online/", "snippet": ""}]}


def test_untrusted_search_hit_is_not_suggested_as_official(monkeypatch):
    out = run(FEE, lambda p: ORGANIC, monkeypatch)
    assert out.verdict == "HIGH_RISK"
    assert "nexora202" not in " ".join(out.next_steps)


def test_knowledge_panel_domain_is_trusted(monkeypatch):
    kg = {"knowledge_graph": {"website": "https://www.nexora.example/"}}
    out = run(FEE, lambda p: kg, monkeypatch)
    assert "nexora.example" in out.next_steps[0]


def test_known_company_list_domain_is_trusted(monkeypatch):
    out = run("Greetings from Wipro Limited. Pay Rs. 500 registration fee to ab@okaxis.", lambda p: {}, monkeypatch)
    assert "wipro.com" in out.next_steps[0]


# ---- the "Wipro | ..." third-party training program email -------------------------------
WIPRO_MAIL = """Wipro | Industry Skill Development & Internship Program Registration Open

Dear Students,
Greetings from the Program Operations Team.
Month 1-2: Industry Training & Mentorship. Month 3: Stipend-Based Internship.
Become eligible for performance-based stipend opportunities of up to ₹25,000, subject to applicable criteria.
Please review the eligibility criteria, applicable fees, stipend terms and other guidelines.
For queries: 9000000011 / 9000000012
Program Operations Team"""

WIPRO_JOBS = {"jobs_results": [{"title": "SOC Analyst", "company_name": "Wipro Limited", "location": "Pune"}]}


def test_wipro_training_program_from_third_party_is_at_least_caution(monkeypatch):
    out = run(WIPRO_MAIL, lambda p: WIPRO_JOBS if p["engine"] == "google_jobs" else {}, monkeypatch,
              sender_email="recruiter@programs-partner.example")
    by = {c.id: c for c in out.checks}
    assert out.extracted.company == "Wipro"
    assert out.verdict in ("CAUTION", "HIGH_RISK")
    assert "THIRD_PARTY_SENDER" in {o.rule for o in out.overrides}
    assert by["job_listing"].status == "warn"            # an unrelated Wipro opening is not confirmation
    assert {"FEES_UNSTATED", "TRAINING_FIRST"} <= set(by["text_red_flags"].flags)
    assert out.verdict != "HIGH_RISK"                     # no fee was demanded: don't overclaim
