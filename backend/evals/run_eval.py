"""Score the pipeline against labelled offers.

Usage (from backend/):  python -m evals.run_eval [--live]
Row format (evals/labeled.jsonl):
  {"id","text","label":"scam|genuine|unclear","source":"real-received|synthetic","note", optional company/sender_email/role}
"unclear" rows are listed for information and excluded from every headline metric.
Metrics are reported for real-received rows, synthetic rows, and combined.
"""
import asyncio
import json
import sys
from pathlib import Path

from app.models import CheckRequest
from app.pipeline import check

HERE = Path(__file__).parent
LABELS = ("scam", "genuine", "unclear")
VERDICTS = ("HIGH_RISK", "CAUTION", "NO_RED_FLAGS", "NOT_ENOUGH_EVIDENCE")
SOURCES = ("real-received", "synthetic")
MIN_ROWS = 20


def top_reason(out) -> str:
    if out.overrides:
        return out.overrides[0].reason
    return next((c.finding for c in out.checks if c.status in ("fail", "warn")), "no red flags")


def frac(n: int, d: int) -> str:
    return f"{n}/{d} ({n / d:.0%})" if d else "n/a (0/0)"


def section(title: str, graded: list) -> str:
    """graded: [(row, output)]"""
    matrix = {l: dict.fromkeys(VERDICTS, 0) for l in LABELS}
    for r, o in graded:
        matrix[r["label"]][o.verdict] += 1
    n = lambda label, *vs: sum(matrix[label][v] for v in vs)
    scam, genuine = sum(matrix["scam"].values()), sum(matrix["genuine"].values())
    total = scam + genuine
    warn = f"\n> **Small sample:** only {total} labelled scam + genuine offers (< {MIN_ROWS}). A smoke test, not accuracy.\n" if total < MIN_ROWS else ""
    rows = "\n".join(f"| **{l}** | " + " | ".join(str(matrix[l][v]) for v in VERDICTS) + f" | {sum(matrix[l].values())} |" for l in LABELS)
    return f"""### {title}: {len(graded)} offers ({scam} scam, {genuine} genuine, {len(graded) - total} unclear)
{warn}
| label \\ verdict | HIGH_RISK | CAUTION | NO_RED_FLAGS | NOT_ENOUGH_EVIDENCE | total |
|---|---|---|---|---|---|
{rows}

| Metric | Result |
|---|---|
| Scam recall (High risk or Caution) | {frac(n("scam", "HIGH_RISK", "CAUTION"), scam)} |
| Strict scam recall (High risk) | {frac(n("scam", "HIGH_RISK"), scam)} |
| False-alarm rate (genuine rated High risk) | {frac(n("genuine", "HIGH_RISK"), genuine)} |
| Caution rate on genuine (not a false alarm) | {frac(n("genuine", "CAUTION"), genuine)} |
"""


async def main(mode: str):
    path = HERE / "labeled.jsonl"
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    bad = [r["id"] for r in rows if r["label"] not in LABELS or r.get("source") not in SOURCES]
    if bad:
        raise SystemExit(f"Bad label (use {LABELS}) or source (use {SOURCES}) in rows: {bad}")

    graded = []
    for r in rows:
        out = await check(CheckRequest(offer_text=r["text"], company=r.get("company"), sender_email=r.get("sender_email"), role=r.get("role")), mode)
        graded.append((r, out))

    tag = lambda r: f"`{r['id']}` [{r['source']}]"
    missed = [f"- {tag(r)} → {o.verdict}: {top_reason(o)}" for r, o in graded if r["label"] == "scam" and o.verdict not in ("HIGH_RISK", "CAUTION")]
    alarms = [f"- {tag(r)} → HIGH_RISK: {top_reason(o)}" for r, o in graded if r["label"] == "genuine" and o.verdict == "HIGH_RISK"]
    unclear = [f"- {tag(r)} → **{o.verdict}**: {top_reason(o)}  _(label note: {r.get('note', '')})_" for r, o in graded if r["label"] == "unclear"]

    parts = [section("Real-received", [g for g in graded if g[0]["source"] == "real-received"]),
             section("Synthetic", [g for g in graded if g[0]["source"] == "synthetic"]),
             section("Combined", graded)]
    report = f"""## Accuracy

Mode: `{mode}`. Headline metrics use scam + genuine rows only; unclear rows are excluded. Synthetic rows are texts we wrote; real-received rows are messages students actually got (personal details replaced with placeholders).

{chr(10).join(parts)}
### Missed scams
{chr(10).join(missed) or "None."}

### False alarms
{chr(10).join(alarms) or "None."}

### Unclear offers (information only)
{chr(10).join(unclear) or "None."}
"""
    (HERE / "report.md").write_text(report, encoding="utf-8")
    sys.stdout.buffer.write(report.encode("utf-8"))


if __name__ == "__main__":
    asyncio.run(main("live" if "--live" in sys.argv else "cached"))
