"""A check that couldn't run says WHY: slow vs broken vs not recorded. Stubbed search, no network."""
import asyncio

import serpapi

import app.pipeline as pl
from app.models import CheckRequest
from app.serp import CacheMiss

OFFER = "Greetings from Zzyzx Corp. Please reply to hr@zzyzx.example to accept your seat today."


class Raising:
    used = 0
    keys: list = []

    def __init__(self, exc):
        self.exc = exc

    def search(self, params):
        raise self.exc


def run(monkeypatch, exc, mode="live"):
    monkeypatch.setattr(pl, "Serp", lambda m: Raising(exc))
    out = asyncio.run(pl.check(CheckRequest(offer_text=OFFER), mode))
    return next(c for c in out.checks if c.id == "registration")


def test_a_slow_serpapi_response_is_reported_as_slow_not_failed(monkeypatch):
    # seen live: SerpApi took 10-64 s on ordinary queries; the client times out at 7 s with this exception, which is
    # a requests Timeout but NOT an asyncio/builtin TimeoutError, so it used to be reported as "The search failed".
    c = run(monkeypatch, serpapi.exceptions.TimeoutError("read timed out"))
    assert c.status == "unknown" and c.skipped == "slow"
    assert "too slow" in c.finding and "failed" not in c.finding


def test_the_per_check_deadline_is_also_slow(monkeypatch):
    class Slow(Raising):
        def search(self, params):
            import time
            time.sleep(0.3)

    monkeypatch.setattr(pl, "CHECK_TIMEOUT", 0.05)
    monkeypatch.setattr(pl, "Serp", lambda m: Slow(None))
    out = asyncio.run(pl.check(CheckRequest(offer_text=OFFER), "live"))
    assert next(c for c in out.checks if c.id == "registration").skipped == "slow"


def test_other_errors_are_failed_and_cached_misses_are_not_recorded(monkeypatch):
    c = run(monkeypatch, RuntimeError("boom"))
    assert c.skipped == "failed" and "failed" in c.finding
    c = run(monkeypatch, CacheMiss("q"), mode="cached")
    assert c.skipped == "not_recorded"


def test_checks_that_ran_have_no_skip_reason(monkeypatch):
    monkeypatch.setattr(pl, "Serp", lambda m: type("S", (), {"used": 0, "keys": [], "search": lambda self, p: __import__("app.serp", fromlist=["Hit"]).Hit({}, "2026-01-01T00:00:00+00:00", False)})())
    out = asyncio.run(pl.check(CheckRequest(offer_text=OFFER), "live"))
    assert next(c for c in out.checks if c.id == "text_red_flags").skipped is None


def test_a_used_up_daily_live_limit_is_reported_as_capped_not_as_unrecorded(monkeypatch):
    from app.serp import CapReached, Serp

    monkeypatch.setenv("LIVE_DAILY_CAP", "0")  # the site's allowance is already spent
    with __import__("pytest").raises(CapReached):
        Serp("live").search({"engine": "google", "q": "a query that is certainly not cached 91827364"})
    assert issubclass(CapReached, CacheMiss)

    c = run(monkeypatch, CapReached("cap"))
    assert c.status == "unknown" and c.skipped == "capped"
    assert "daily limit of live searches" in c.finding and "No recorded search" not in c.finding
