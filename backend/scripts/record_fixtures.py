"""Record the searches the samples and eval rows need into fixtures/ (so MODE=cached works offline).

Only searches MISSING from fixtures/ are made; existing fixtures are never re-recorded. Shows how many
it will make and asks first (--yes skips the question). Fixtures are raw SerpApi responses, never edited.

Uses a 20s timeout and copies a response the moment it arrives, even if the check already gave up on it.
Usage (from backend/):  python -m scripts.record_fixtures [--yes]
"""
import os

os.environ["SEARCH_TIMEOUT_SECONDS"] = "20"  # must be set before app modules read it

import asyncio  # noqa: E402
import json  # noqa: E402
import shutil  # noqa: E402
import sys  # noqa: E402

from app import pipeline  # noqa: E402
from app.models import CheckRequest  # noqa: E402
from app.samples import SAMPLES  # noqa: E402
from app.serp import CACHE, FIXTURES, CacheMiss, Hit, Serp, cache_key  # noqa: E402

EVAL_ROWS = pipeline.__file__.rsplit("app", 1)[0] + "evals/labeled.jsonl"


def requests() -> list[CheckRequest]:
    reqs = [CheckRequest(**{k: v for k, v in s.items() if k != "label"}) for s in SAMPLES.values()]
    seen = {r.offer_text for r in reqs}
    if os.path.exists(EVAL_ROWS):
        for line in open(EVAL_ROWS, encoding="utf-8"):
            if line.strip():
                row = json.loads(line)
                if row["text"] not in seen:
                    seen.add(row["text"])
                    reqs.append(CheckRequest(offer_text=row["text"], company=row.get("company"),
                                             sender_email=row.get("sender_email"), role=row.get("role")))
    return reqs


def full(params: dict) -> dict:
    return {"gl": "in", "hl": "en", **params}


missing: dict[str, dict] = {}


class Planner(Serp):
    """Cached-mode lookups that remember what is absent. A missing search makes its check 'unknown', so
    searches that depend on it are not seen yet: the count is a lower bound."""

    def search(self, params):
        try:
            return super().search(params)
        except CacheMiss:
            missing[cache_key(full(params))] = full(params)
            raise


made = 0
copied: set[str] = set()


class Recording(Serp):
    def search(self, params):
        global made
        k = cache_key(full(params))
        fx = FIXTURES / f"{k}.json"
        if fx.exists():  # never re-record
            blob = json.loads(fx.read_text(encoding="utf-8"))
            return Hit(blob["data"], blob["retrieved_at"], True)
        hit = super().search(params)  # disk cache first, otherwise the API; returns whenever the response arrives
        if not hit.from_cache:
            made += 1
        shutil.copy(CACHE / f"{k}.json", fx)
        copied.add(k)
        return hit


async def main(yes: bool):
    FIXTURES.mkdir(exist_ok=True)
    reqs = requests()
    pipeline.Serp = Planner
    for r in reqs:
        await pipeline.check(r, "cached")
    from_cache = [k for k in missing if (CACHE / f"{k}.json").exists()]
    api = len(missing) - len(from_cache)
    print(f"{len(reqs)} offers. {len(missing)} searches are missing from fixtures/: "
          f"{len(from_cache)} already in the local cache (free), {api} would be NEW SerpApi searches.")
    print("(A lower bound: searches that depend on these results are only discovered once they exist; "
          "at most ~11 per offer.)")
    if not missing:
        return print("Nothing to record.")
    if not yes:
        try:
            ok = input(f"Make up to {api} live searches and record them? [y/N] ").strip().lower() == "y"
        except EOFError:
            ok = False
        if not ok:
            return print("Aborted. Nothing was spent.")

    pipeline.Serp = Recording
    for r in reqs:
        out = await pipeline.check(r, "live")
        print(f"  {(r.company or r.offer_text[:30]):32} {out.verdict}")
    print(f"Done: {made} new SerpApi searches made, {len(copied)} searches copied into fixtures/.")


if __name__ == "__main__":
    asyncio.run(main("--yes" in sys.argv))  # shutdown waits for still-running search threads, so late responses are copied too
