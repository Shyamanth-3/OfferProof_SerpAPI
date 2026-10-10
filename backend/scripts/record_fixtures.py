"""Record the searches the samples, journey samples and eval rows need into fixtures/ (so MODE=cached works offline).

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

from app import journey, pipeline  # noqa: E402
from app.models import CheckRequest, JourneyInput  # noqa: E402
from app.samples import JOURNEY_SAMPLES, SAMPLES  # noqa: E402
from app.serp import CACHE, FIXTURES, CacheMiss, Hit, Serp, cache_key  # noqa: E402

EVAL_ROWS = pipeline.__file__.rsplit("app", 1)[0] + "evals/labeled.jsonl"


def jobs() -> list[tuple[str, callable]]:
    """(label, mode -> coroutine) for every quick sample, eval row and journey sample."""
    out = []
    reqs = [(k, CheckRequest(**{f: v for f, v in s.items() if f not in ("label", "kind")})) for k, s in SAMPLES.items()]
    seen = {r.offer_text for _, r in reqs}
    if os.path.exists(EVAL_ROWS):
        for line in open(EVAL_ROWS, encoding="utf-8"):
            if line.strip():
                row = json.loads(line)
                if row["text"] not in seen:
                    seen.add(row["text"])
                    reqs.append((row["id"], CheckRequest(offer_text=row["text"], company=row.get("company"),
                                                         sender_email=row.get("sender_email"), role=row.get("role"))))
    for name, r in reqs:
        out.append((name, lambda mode, r=r: pipeline.check(r, mode)))
    for name, s in JOURNEY_SAMPLES.items():
        out.append((name, lambda mode, j=JourneyInput(**s["journey"]): journey.investigate(j, mode)))
    return out


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
    todo = jobs()
    pipeline.Serp = Planner
    for _, fn in todo:
        await fn("cached")
    from_cache = [k for k in missing if (CACHE / f"{k}.json").exists()]
    api = len(missing) - len(from_cache)
    print(f"{len(todo)} offers/journeys. {len(missing)} searches are missing from fixtures/: "
          f"{len(from_cache)} already in the local cache (free), {api} would be NEW SerpApi searches.")
    for p in missing.values():
        print(f"   {p['engine']:12} {p.get('q', '')[:100]}")
    print("(A lower bound: searches that depend on these results are only discovered once they exist.)")
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
    for name, fn in todo:
        out = await fn("live")
        print(f"  {name[:34]:34} {out.verdict}")
    print(f"Done: {made} new SerpApi searches made, {len(copied)} searches copied into fixtures/.")


if __name__ == "__main__":
    asyncio.run(main("--yes" in sys.argv))  # shutdown waits for still-running search threads, so late responses are copied too
