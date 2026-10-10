## Accuracy

Mode: `live`. Headline metrics use scam + genuine rows only; unclear rows are excluded. Synthetic rows are texts we wrote; real-received rows are messages students actually got (personal details replaced with placeholders).

### Real-received: 2 offers (1 scam, 0 genuine, 1 unclear)

> **Small sample:** only 1 labelled scam + genuine offers (< 20). A smoke test, not accuracy.

| label \ verdict | HIGH_RISK | CAUTION | NO_RED_FLAGS | NOT_ENOUGH_EVIDENCE | total |
|---|---|---|---|---|---|
| **scam** | 0 | 1 | 0 | 0 | 1 |
| **genuine** | 0 | 0 | 0 | 0 | 0 |
| **unclear** | 0 | 1 | 0 | 0 | 1 |

| Metric | Result |
|---|---|
| Scam recall (High risk or Caution) | 1/1 (100%) |
| Strict scam recall (High risk) | 0/1 (0%) |
| False-alarm rate (genuine rated High risk) | n/a (0/0) |
| Caution rate on genuine (not a false alarm) | n/a (0/0) |

### Synthetic: 6 offers (3 scam, 2 genuine, 1 unclear)

> **Small sample:** only 5 labelled scam + genuine offers (< 20). A smoke test, not accuracy.

| label \ verdict | HIGH_RISK | CAUTION | NO_RED_FLAGS | NOT_ENOUGH_EVIDENCE | total |
|---|---|---|---|---|---|
| **scam** | 3 | 0 | 0 | 0 | 3 |
| **genuine** | 0 | 0 | 2 | 0 | 2 |
| **unclear** | 0 | 1 | 0 | 0 | 1 |

| Metric | Result |
|---|---|
| Scam recall (High risk or Caution) | 3/3 (100%) |
| Strict scam recall (High risk) | 3/3 (100%) |
| False-alarm rate (genuine rated High risk) | 0/2 (0%) |
| Caution rate on genuine (not a false alarm) | 0/2 (0%) |

### Combined: 8 offers (4 scam, 2 genuine, 2 unclear)

> **Small sample:** only 6 labelled scam + genuine offers (< 20). A smoke test, not accuracy.

| label \ verdict | HIGH_RISK | CAUTION | NO_RED_FLAGS | NOT_ENOUGH_EVIDENCE | total |
|---|---|---|---|---|---|
| **scam** | 3 | 1 | 0 | 0 | 4 |
| **genuine** | 0 | 0 | 2 | 0 | 2 |
| **unclear** | 0 | 2 | 0 | 0 | 2 |

| Metric | Result |
|---|---|
| Scam recall (High risk or Caution) | 4/4 (100%) |
| Strict scam recall (High risk) | 3/4 (75%) |
| False-alarm rate (genuine rated High risk) | 0/2 (0%) |
| Caution rate on genuine (not a false alarm) | 0/2 (0%) |

### Missed scams
None.

### False alarms
None.

### Unclear offers (information only)
- `UNCLEAR_STARTUP` [synthetic] → **CAUTION**: The offer came from a free mail address, not the company's own domain.  _(label note: Small startup writing from Gmail; no fee, no pressure; could be real.)_
- `REAL_WIPRO_THIRD_PARTY` [real-received] → **CAUTION**: The offer names Wipro, but it was sent from programs-partner.example, which is not a Wipro domain.  _(label note: Third-party program using Wipro's name in the subject, sender on a different domain, fees unstated, training before stipend. Not provably fraud.)_
