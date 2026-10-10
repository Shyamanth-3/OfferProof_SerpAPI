"""The live-search guards: daily cap, and a reserve of the real SerpApi balance. No network."""
import pytest

import app.serp as serp
from app.serp import CapReached, Serp


class Account:
    """Stands in for requests.get('.../account.json')."""

    def __init__(self, left=None, boom=False):
        self.left, self.boom, self.calls = left, boom, 0

    def __call__(self, url, params=None, timeout=None):
        self.calls += 1
        if self.boom:
            raise RuntimeError("account endpoint down")
        acct = self
        return type("R", (), {"json": lambda s: {"total_searches_left": acct.left}})()


@pytest.fixture(autouse=True)
def fresh(monkeypatch):
    monkeypatch.setattr(serp, "_bal", {"at": 0.0, "left": None})
    monkeypatch.setenv("LIVE_DAILY_CAP", "1000")
    monkeypatch.setattr(Serp, "_call", staticmethod(lambda params: {"organic_results": []}))  # no real API call
    monkeypatch.setattr(serp, "CACHE", serp.CACHE.parent / "cache_test_reserve")
    yield
    import shutil
    shutil.rmtree(serp.CACHE, ignore_errors=True)


def search(q="reserve test 1"):
    return Serp("live").search({"engine": "google", "q": q})


def test_no_reserve_means_the_account_is_never_asked(monkeypatch):
    acct = Account(left=5)
    monkeypatch.setattr(serp.requests, "get", acct)
    monkeypatch.delenv("LIVE_RESERVE", raising=False)
    assert search().data == {"organic_results": []} and acct.calls == 0


def test_live_searching_stops_at_the_reserve(monkeypatch):
    monkeypatch.setenv("LIVE_RESERVE", "100")
    monkeypatch.setattr(serp.requests, "get", Account(left=100))
    with pytest.raises(CapReached):
        search("at the reserve")
    monkeypatch.setattr(serp, "_bal", {"at": 0.0, "left": None})
    monkeypatch.setattr(serp.requests, "get", Account(left=101))
    assert search("just above the reserve").data == {"organic_results": []}


def test_the_balance_is_read_once_a_minute_and_counted_down_locally(monkeypatch):
    monkeypatch.setenv("LIVE_RESERVE", "100")
    acct = Account(left=102)
    monkeypatch.setattr(serp.requests, "get", acct)
    search("one")  # 102 -> counts down to 101
    search("two")  # 101 -> 100, still allowed because 101 > 100 was checked first
    with pytest.raises(CapReached):
        search("three")  # now at 100: refused, without asking the account again
    assert acct.calls == 1


def test_an_unreadable_balance_refuses_live_searches(monkeypatch):
    monkeypatch.setenv("LIVE_RESERVE", "100")
    monkeypatch.setattr(serp.requests, "get", Account(boom=True))
    with pytest.raises(CapReached):
        search("balance unknown")


def test_the_daily_cap_still_applies(monkeypatch):
    monkeypatch.setenv("LIVE_DAILY_CAP", "0")
    monkeypatch.delenv("LIVE_RESERVE", raising=False)
    with pytest.raises(CapReached):
        search("capped for the day")


def test_cached_answers_never_touch_either_guard(monkeypatch):
    monkeypatch.setenv("LIVE_DAILY_CAP", "0")
    monkeypatch.setenv("LIVE_RESERVE", "100")
    acct = Account(left=0)
    monkeypatch.setattr(serp.requests, "get", acct)
    # same query twice: the first is allowed only because guards are off for this line, the second must be a cache hit
    monkeypatch.setenv("LIVE_DAILY_CAP", "1000")
    monkeypatch.setenv("LIVE_RESERVE", "0")
    search("cache me")
    monkeypatch.setenv("LIVE_DAILY_CAP", "0")
    monkeypatch.setenv("LIVE_RESERVE", "100")
    assert search("cache me").from_cache and acct.calls == 0
