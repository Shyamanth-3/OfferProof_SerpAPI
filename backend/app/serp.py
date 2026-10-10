"""SerpApi wrapper: disk cache, recorded fixtures, per-request call counter."""
import hashlib
import json
import os
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")
CACHE, FIXTURES = ROOT / "cache", ROOT / "fixtures"
# HTTP timeout sits 1s under the per-check timeout (pipeline.CHECK_TIMEOUT), both from SEARCH_TIMEOUT_SECONDS
TIMEOUT = float(os.getenv("SEARCH_TIMEOUT_SECONDS", "8")) - 1


class CacheMiss(Exception):
    pass


class CapReached(CacheMiss):
    """The site's daily limit of live searches is used up. A CacheMiss, so callers that only care that no result
    exists keep working, but the pipeline can tell the student the real reason."""


@dataclass
class Hit:
    data: dict
    retrieved_at: str
    from_cache: bool


def cache_key(params: dict) -> str:
    clean = {k: v for k, v in params.items() if k != "api_key"}
    return hashlib.sha256(json.dumps(clean, sort_keys=True).encode()).hexdigest()[:32]


# ponytail: in-memory daily cap resets on restart; persist it if the service gets public traffic
_cap = {"day": None, "n": 0}
_cap_lock = threading.Lock()


def _take_live_slot() -> bool:
    with _cap_lock:
        today = date.today()
        if _cap["day"] != today:
            _cap.update(day=today, n=0)
        if _cap["n"] >= int(os.getenv("LIVE_DAILY_CAP", "200")):
            return False
        _cap["n"] += 1
        return True


# The daily counter above resets whenever a free host restarts, so the real SerpApi balance is the stronger guard:
# with LIVE_RESERVE set, live searching stops once the account balance is down to that many searches. The balance
# endpoint is free; it is read at most once a minute and counted down locally in between. If it can't be read,
# live searches are refused (the quota matters more than one check).
_bal = {"at": 0.0, "left": None}


def _reserve_ok() -> bool:
    reserve = int(os.getenv("LIVE_RESERVE", "0"))
    if reserve <= 0:
        return True
    with _cap_lock:
        stale = _bal["left"] is None or time.monotonic() - _bal["at"] > 60
    if stale:
        try:
            r = requests.get("https://serpapi.com/account.json", params={"api_key": os.getenv("SERPAPI_API_KEY", "")}, timeout=5)
            left = r.json().get("total_searches_left")
        except Exception:
            left = None
        with _cap_lock:
            _bal.update(at=time.monotonic(), left=left)
    with _cap_lock:
        return _bal["left"] is not None and _bal["left"] > reserve


def _spent_one() -> None:
    with _cap_lock:
        if _bal["left"] is not None:
            _bal["left"] -= 1


class Serp:
    """One per request. `used` counts real API calls; `keys` lists cache files touched."""

    def __init__(self, mode: str):
        self.mode, self.used, self.keys = mode, 0, []
        self._lock = threading.Lock()

    def search(self, params: dict) -> Hit:
        params = {"gl": "in", "hl": "en", **params}
        k = cache_key(params)
        self.keys.append(k)
        dirs = [CACHE, FIXTURES] if self.mode == "cached" else [CACHE]
        for d in dirs:
            f = d / f"{k}.json"
            if f.exists():
                blob = json.loads(f.read_text(encoding="utf-8"))
                return Hit(blob["data"], blob["retrieved_at"], True)
        if self.mode == "cached":
            raise CacheMiss(params.get("q", ""))
        if not _reserve_ok() or not _take_live_slot():
            raise CapReached("live-search allowance used up")
        data = self._call(params)
        _spent_one()
        with self._lock:
            self.used += 1
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        CACHE.mkdir(exist_ok=True)
        (CACHE / f"{k}.json").write_text(json.dumps({"retrieved_at": now, "data": data}), encoding="utf-8")
        return Hit(data, now, False)

    @staticmethod
    def _call(params: dict) -> dict:
        import serpapi

        key = os.getenv("SERPAPI_API_KEY", "")
        if not key or key.startswith("PASTE_"):
            raise RuntimeError("SERPAPI_API_KEY is not set")
        try:
            return dict(serpapi.Client(api_key=key, timeout=TIMEOUT).search(params))
        except serpapi.SerpApiError as e:
            if "hasn't returned any results" in str(e):  # a valid "nothing found" answer
                return {}
            raise
