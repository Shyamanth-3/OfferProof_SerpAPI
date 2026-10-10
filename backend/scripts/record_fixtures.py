"""Run every sample live and copy each search into fixtures/ (so MODE=cached works offline).

Uses a 20s timeout and copies a response the moment it arrives, even if the check already gave up on it.
Usage (from backend/):  python -m scripts.record_fixtures
"""
import os

os.environ["SEARCH_TIMEOUT_SECONDS"] = "20"  # must be set before app modules read it

import asyncio  # noqa: E402
import shutil  # noqa: E402

from app import pipeline  # noqa: E402
from app.models import CheckRequest  # noqa: E402
from app.samples import SAMPLES  # noqa: E402
from app.serp import CACHE, FIXTURES, Serp, cache_key  # noqa: E402

copied: set[str] = set()


class Recording(Serp):
    def search(self, params):
        hit = super().search(params)  # returns whenever the response arrives; runs in the worker thread
        k = cache_key({"gl": "in", "hl": "en", **params})
        shutil.copy(CACHE / f"{k}.json", FIXTURES / f"{k}.json")
        copied.add(k)
        return hit


async def main():
    pipeline.Serp = Recording
    FIXTURES.mkdir(exist_ok=True)
    for name, s in SAMPLES.items():
        out = await pipeline.check(CheckRequest(**{k: v for k, v in s.items() if k != "label"}), "live")
        print(f"{name:22} {out.verdict:20} live searches: {out.searches_used}")
    print(f"{len(copied)} searches copied to fixtures/")


if __name__ == "__main__":
    asyncio.run(main())  # shutdown waits for any still-running search threads, so late responses are copied too
