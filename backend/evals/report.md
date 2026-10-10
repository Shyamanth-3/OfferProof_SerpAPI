## Accuracy

Evaluated on 5 labelled offers (2 scam, 2 genuine, 1 unclear) · mode: `cached`

> **Small sample:** only 4 labelled scam + genuine offers (< 20). Treat these numbers as a smoke test, not accuracy.

| label \ verdict | HIGH_RISK | CAUTION | NO_RED_FLAGS | NOT_ENOUGH_EVIDENCE | total |
|---|---|---|---|---|---|
| **scam** | 2 | 0 | 0 | 0 | 2 |
| **genuine** | 0 | 0 | 2 | 0 | 2 |
| **unclear** | 0 | 1 | 0 | 0 | 1 |

Headline metrics use scam + genuine rows only; unclear rows are excluded.

| Metric | Result | Definition |
|---|---|---|
| Scam recall | 2/2 (100%) | scams rated High risk or Caution |
| Strict scam recall | 2/2 (100%) | scams rated High risk |
| False-alarm rate | 0/2 (0%) | genuine offers rated High risk |
| Caution rate on genuine | 0/2 (0%) | genuine offers rated Caution (not a false alarm: the tool advises verifying) |

### Missed scams
None.

### False alarms
None.

### Unclear offers (information only)
- `UNCLEAR_STARTUP` → **CAUTION**: The offer came from a free mail address, not the company's own domain.
