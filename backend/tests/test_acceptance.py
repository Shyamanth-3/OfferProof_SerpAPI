"""The 5 samples end-to-end in cached mode (recorded fixtures only, no network)."""
import asyncio

import pytest

from app.models import CheckRequest
from app.pipeline import check
from app.samples import SAMPLES


def run(name):
    s = SAMPLES[name]
    req = CheckRequest(**{k: v for k, v in s.items() if k != "label"})
    return asyncio.run(check(req, "cached"))


def test_scam_fee():
    out = run("SCAM_FEE")
    assert out.verdict == "HIGH_RISK" and "FEE_DEMANDED" in {o.rule for o in out.overrides}


def test_impersonation():
    out = run("IMPERSONATION")
    assert out.verdict == "HIGH_RISK" and "LOOKALIKE_DOMAIN" in {o.rule for o in out.overrides}


def test_genuine_negated_fee():
    out = run("GENUINE_NEGATED_FEE")
    assert out.verdict != "HIGH_RISK"
    assert "FEE" not in next(c for c in out.checks if c.id == "text_red_flags").flags


def test_unclear_startup():
    assert run("UNCLEAR_STARTUP").verdict in ("CAUTION", "NOT_ENOUGH_EVIDENCE")


def test_genuine_big_brand():
    assert run("GENUINE_BIG_BRAND").verdict != "HIGH_RISK"
