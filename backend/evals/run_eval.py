"""Score the pipeline against labelled offers.

Usage (from backend/):  python -m evals.run_eval [--live]
Row format (evals/labeled.jsonl): {"id","text","label":"scam|genuine|unclear","source", optional company/sender_email/role}
"unclear" rows are listed for information and excluded from every headline metric.
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
MIN_ROWS = 20


def seed_rows():
    from app.samples import SAMPLES

    labels = {"SCAM_FEE": "scam", "IMPERSONATION": "scam", "UNCLEAR_STARTUP": "unclear"}
    return [
        {"id": k, "text": s["offer_text"], "label": labels.get(k, "genuine"), "source": "seed sample",
         **{f: s[f] for f in ("company", "sender_email", "role") if f in s}}
        for k, s in SAMPLES.items()
    ]


def top_reason(out) -> str:
    if out.overrides:
        return out.overrides[0].reason
    return next((c.finding for c in out.checks if c.status in ("fail", "warn")), "no red flags")


def frac(n: int, d: int) -> str:
    return f"{n}/{d} ({n / d:.0%})" if d else "n/a (0/0)"


async def main(mode: str):
    path = HERE / "labeled.jsonl"
    if not path.exists():
        path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in seed_rows()) + "\n", encoding="utf-8")
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    bad = [r["id"] for r in rows if r["label"] not in LABELS]
    if bad:
        raise SystemExit(f"Unknown label (use {LABELS}) in rows: {bad}")

    matrix = {l: dict.fromkeys(VERDICTS, 0) for l in LABELS}
    graded = []  # (row, output)
    for r in rows:
        out = await check(CheckRequest(offer_text=r["text"], company=r.get("company"), sender_email=r.get("sender_email"), role=r.get("role")), mode)
        matrix[r["label"]][out.verdict] += 1
        graded.append((r, out))

    def n(label, *verdicts):
        return sum(matrix[label][v] for v in verdicts)

    scam, genuine = sum(matrix["scam"].values()), sum(matrix["genuine"].values())
    total = scam + genuine
    warn = f"\n> **Small sample:** only {total} labelled scam + genuine offers (< {MIN_ROWS}). Treat these numbers as a smoke test, not accuracy.\n" if total < MIN_ROWS else ""

    table = "\n".join(
        f"| **{l}** | " + " | ".join(str(matrix[l][v]) for v in VERDICTS) + f" | {sum(matrix[l].values())} |" for l in LABELS
    )
    missed = [f"- `{r['id']}` → {o.verdict}: {top_reason(o)}" for r, o in graded if r["label"] == "scam" and o.verdict not in ("HIGH_RISK", "CAUTION")]
    alarms = [f"- `{r['id']}` → HIGH_RISK: {top_reason(o)}" for r, o in graded if r["label"] == "genuine" and o.verdict == "HIGH_RISK"]
    unclear = [f"- `{r['id']}` → **{o.verdict}**: {top_reason(o)}" for r, o in graded if r["label"] == "unclear"]

    report = f"""## Accuracy

Evaluated on {len(rows)} labelled offers ({scam} scam, {genuine} genuine, {len(rows) - total} unclear) · mode: `{mode}`
{warn}
| label \\ verdict | HIGH_RISK | CAUTION | NO_RED_FLAGS | NOT_ENOUGH_EVIDENCE | total |
|---|---|---|---|---|---|
{table}

Headline metrics use scam + genuine rows only; unclear rows are excluded.

| Metric | Result | Definition |
|---|---|---|
| Scam recall | {frac(n("scam", "HIGH_RISK", "CAUTION"), scam)} | scams rated High risk or Caution |
| Strict scam recall | {frac(n("scam", "HIGH_RISK"), scam)} | scams rated High risk |
| False-alarm rate | {frac(n("genuine", "HIGH_RISK"), genuine)} | genuine offers rated High risk |
| Caution rate on genuine | {frac(n("genuine", "CAUTION"), genuine)} | genuine offers rated Caution (not a false alarm: the tool advises verifying) |

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
