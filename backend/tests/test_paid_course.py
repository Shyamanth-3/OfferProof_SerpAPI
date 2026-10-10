"""A genuine-domain 'internship' that is really a paid-course funnel with a job guarantee."""
import asyncio

import app.pipeline as pl
from app.checks import text_red_flags
from app.extract import extract
from app.models import CheckRequest
from app.serp import Hit

MAIL = """Welcome Onboard – Examplelearn Internship + AWS & Microsoft Certification Path
External
Inbox
Careers Examplelearn <careers@examplelearn.example>
Tue, Jul 14, 8:55 PM
to jv, bcc: me
Dear Student,
Congratulations and welcome to the Examplelearn Internship & Skill Development Program!
At Examplelearn, we believe in learning by doing. Our program blends mentorship, certifications, and guaranteed placements.
Skill Boost Program (100% Job Guarantee) – train for placements.
Program Benefits:
100% Job Guarantee after course completion
Certifications from MNCs, AWS & AICTE
Phase 1 – Core Training (20 Days)
Enroll Now
https://forms.gle/kur4DXDUrHwXXbPT7
Team Examplelearn"""


class Stub:
    used = 0
    keys: list = []

    def search(self, params):
        return Hit({}, "2026-01-01T00:00:00+00:00", False)


def test_company_comes_from_sender_domain_not_a_stray_phrase():
    e = extract(MAIL)
    assert e.sender_email == "careers@examplelearn.example"
    assert e.company == "Examplelearn"  # not "MNCs" (from "Certifications from MNCs, AWS & AICTE")


def test_list_like_from_phrase_is_not_a_company():
    assert extract("Get certifications from MNCs, AWS & AICTE today.").company is None
    assert extract("We are hiring an intern at Infosys Limited this summer.").company == "Infosys Limited"


def test_job_guarantee_and_course_selling_flags():
    f = text_red_flags.detect(MAIL)
    assert {"JOB_GUARANTEE", "COURSE_SELLING"} <= set(f) and "FEE" not in f


def test_flags_stay_quiet_on_negation_and_ordinary_offers():
    assert "JOB_GUARANTEE" not in text_red_flags.detect("We do not offer any job guarantee or guaranteed placement.")
    assert not text_red_flags.detect("Your internship may lead to a full-time role based on performance. Placement is not guaranteed.")


def test_examplelearn_mail_is_at_least_caution(monkeypatch):
    monkeypatch.setattr(pl, "Serp", lambda mode: Stub())
    out = asyncio.run(pl.check(CheckRequest(offer_text=MAIL), "live"))
    assert out.verdict in ("CAUTION", "HIGH_RISK")
    assert "JOB_GUARANTEE" in {o.rule for o in out.overrides}
    assert out.verdict != "HIGH_RISK"  # no fee was demanded; don't overclaim
