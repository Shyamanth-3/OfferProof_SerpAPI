<div align="center">

# OfferProof

### The company is real. The offer isn't.

**Paste a job or internship offer. We check whether it can actually be traced back to the company it claims to be from, using live search evidence and fixed rules. No AI decides.**

[**Live demo**](https://offerproof.onrender.com/) · [Demo video](#demo) · [How it works](#how-it-works) · [Accuracy](#accuracy-honestly-reported)

![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-TypeScript-61DAFB?logo=react&logoColor=black)
![Tailwind](https://img.shields.io/badge/Tailwind-v4-06B6D4?logo=tailwindcss&logoColor=white)
![SerpApi](https://img.shields.io/badge/Evidence-SerpApi-E5322D)
![Decided by](https://img.shields.io/badge/Verdict%20decided%20by-fixed%20rules%2C%20not%20AI-111111)

SerpApi India Hackathon 2026 · Track 05: Knowledge & Public Interest

</div>

---

## The problem

Every year, students lose money, documents and trust to fake internship and job offers. The scam has changed. The company in the message is usually **real**: a big recruiter, a known startup, a genuine logo. The offer is the fake part, sent from a lookalike domain, a Gmail address or a Telegram handle, and followed by a "registration fee".

So "is this company real?" is the wrong question. Searching for the company name will always say yes.

> **The right question: can this offer be traced back to the company it claims to be from?**

OfferProof answers that. For every finding, it shows the live search result behind it.

## Demo

<!-- Replace with a 30-second GIF or the 90-second video -->
![OfferProof demo](docs/demo.gif)

Try it: **https://offerproof.onrender.com/**. The sample chips run on recorded results and work instantly. Typed text runs live.

---

## What it does

### Quick check
Paste an offer or upload a screenshot. You get a verdict, the evidence behind it, and a **Verify it yourself** kit.

| Verdict | Meaning |
|---|---|
| 🔴 **High risk** | Hard evidence, such as a fee demand, a lookalike domain or a reported scam identifier |
| 🟠 **Caution** | Warning signs such as a free-mail sender or an off-platform-only process |
| 🟢 **No red flags found** | Nothing found against it. **Still, never pay to get hired.** |
| ⚪ **We couldn't verify this** | Not enough evidence, so here is how to check it yourself |

OfferProof **never says "safe"**. A missing result is `unknown`, never a pass.

### Investigate the full journey
Scams aren't one message. They are a journey: a listing, a recruiter, an interview (or none), a payment request, then an offer. This mode checks each stage and draws a **timeline**. It marks **the first point where your journey left the company's real hiring process**.

```
Listing ──▶ Recruiter ──▶ Interview ──▶ Payment ──▶ Offer
  ✔            ✖ ◀── "Your journey left the company's real process here:
                       contacted on Telegram from a Gmail address"
```

---

## How it works

```
 offer text / screenshot
          │
          ▼
  ┌───────────────┐   Aadhaar / PAN → [REDACTED]
  │ 1. Redact     │   screenshots are read on-device (OCR), never uploaded
  └───────┬───────┘
          ▼
  ┌───────────────┐   company · sender · phone · UPI · links · role · pay
  │ 2. Extract    │   (regex + rules)
  └───────┬───────┘
          ▼
  ┌───────────────────────────────────────────────────────────────┐
  │ 3. Evidence: parallel SerpApi searches (8 s timeout each)       │
  │    sender identity · payment-ID trace · wording trace ·         │
  │    job listing · registration · fraud notices · news            │
  └───────┬───────────────────────────────────────────────────────┘
          ▼
  ┌───────────────┐   weighted score + coverage, hard overrides
  │ 4. Fixed rules│   overrides can only RAISE severity
  └───────┬───────┘
          ▼
   verdict · evidence cards · verify kit · (journey) timeline
```

> **Search gathers evidence. Fixed, deterministic rules decide. There is no LLM anywhere in the product.**

### Where SerpApi comes in

SerpApi is the evidence layer. Each check uses a different, independent source:

| Check | SerpApi source | What it proves |
|---|---|---|
| **Sender identity** (30) | Google + knowledge panel | Does the sender's email or domain belong to the company's real website? Detects lookalikes, free-mail and third-party senders |
| **Message red flags** (30) | Fixed rules | Fee demands, off-platform chat, no interview, urgency, unrealistic pay, task scams, Hinglish included |
| **Payment ID and contact trace** (25) | Google | Public scam reports tied to the UPI ID, phone, Telegram handle or link in the offer |
| **Wording trace** (20) | Google, exact-phrase queries | The same text reused under other names, which marks it as a template |
| **Job listing** (10) | Google Jobs | Does this role actually exist? |
| **Company registration** (5) | Google | Is there a registered entity? |
| Fraud notices *(context)* | Google `site:` | Has the company warned about fake offers? |
| Official careers page *(context)* | Google | Where to compare, shown only from a trusted domain |
| Brand impersonation *(context)* | Google News | Is the brand being impersonated right now? |

**Journey mode adds:** listing source, listing clone detection, interview process, listing-vs-offer consistency, and recruiter trace.

### Wording trace in three lines
1. Pick up to two distinctive 8–12 word phrases from the offer.
2. Search them as exact phrases.
3. If results contain the phrase verbatim under other brands or in scam reports, the offer is a reused template. *(It only fires when the scam's wording has been posted publicly.)*

### How the verdict is decided
- `score = points ÷ scored weight × 100`. `unknown` and `info` results are excluded from both sides.
- `coverage = scored weight ÷ total weight`. Below 50% coverage the answer is "We couldn't verify this".
- ≥ 55 is High, ≥ 25 is Caution.
- **Overrides only raise severity.**
  - High: `FEE_DEMANDED`, `LOOKALIKE_DOMAIN`, `IDENTIFIER_REPORTED`, `TEMPLATE_REPORTED`, and in journey mode `PAYMENT_IN_PROCESS`, `COMPANY_MISMATCH`, `LOOKALIKE_LISTING`.
  - Caution: `FREE_MAIL_SENDER`, `OFF_PLATFORM_ONLY`, `THIRD_PARTY_SENDER`, `JOB_GUARANTEE`, and in journey mode `NO_REAL_INTERVIEW`.

### Verify it yourself
Every actionable item in the kit comes **only from a trusted official domain**: a message template to copy, the company's own website, and an email link with no pre-filled recipient. It never includes the student's name, phone, email, Aadhaar or PAN.

---

## Hard problems we solved

- **Lookalikes vs short names.** `hcl` must not fuzzy-match `tcs`. Edit-distance matching applies only to names of 5+ characters, plus token-boundary rules for brand-with-extra-words and hyphenated lookalikes.
- **Mail domain ≠ web domain.** A company can send mail from a different domain than its website (for example `zohocorp.com`), so a seed list covers the big recruiters.
- **A scam site ranking first.** The top organic result is *untrusted*. Only the knowledge-panel website or the seed list can make a domain trusted. A sender matching an untrusted domain gets a warning, never a pass.
- **Negation-aware fee rules.** "No registration fee" must not trigger the fee flag. Negation is clause-bounded and handles Hinglish.
- **`unknown` ≠ safe.** Missing evidence is excluded from the score and lowers coverage, instead of counting as good news.
- **Paid-course traps.** "Training first" and course-selling are soft flags, separate from hard fee demands.
- **Text-reuse fingerprinting.** Generic phrases like "work from home data entry internship" appear on legitimate job boards, so boards are ignored and results must contain the phrase verbatim.
- **Aadhaar vs `wa.me/91…`.** The redactor removes Aadhaar and PAN numbers without mangling WhatsApp links.

## Privacy

- Aadhaar and PAN numbers are **redacted before anything is searched**, and the UI shows how many were removed.
- Screenshot text is extracted **on your device** with tesseract.js. The image is never uploaded. *(The OCR engine and language data load once from the jsDelivr CDN.)*
- Listing URLs are **never fetched**, only their domain is read.
- Real messages in the evaluation set are scrubbed of victims' personal details. The scammer's identifiers are kept as evidence, and a script checks this in CI.
- No accounts, no database of submissions.

---

## Accuracy, honestly reported

<!-- Paste backend/evals/report.md here. Keep the three groups separate. -->

| Set | Source | Notes |
|---|---|---|
| Real-received | Offers students actually received | _fill from report.md_ |
| Real-public | Offers quoted in public complaint posts | _fill from report.md_ |
| Synthetic | Written by us to cover edge cases | _fill from report.md_, **not** evidence of real-world accuracy |

We report the groups separately so synthetic results never inflate the real ones. Ambiguous cases are labelled `unclear` and left out of the false-positive figure.

## What we deliberately don't claim

- ❌ That an offer is **safe**. The best result is "No red flags found," with the advice to never pay to get hired.
- ❌ That AI detects scams. There is no LLM. Every verdict is reproducible from its evidence.
- ❌ That no result means no scam. Absence of evidence is `unknown`.
- ❌ That wording trace catches new scams. It only fires when the wording has already been posted publicly.
- ❌ That a public profile proves a recruiter is real. It's context only, and never a pass.

---

## Run it locally

```bash
git clone https://github.com/YOUR-USER/OfferProof.git
cd OfferProof

# backend
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # add SERPAPI_API_KEY for live mode (optional)
uvicorn app.main:app --reload

# frontend (new terminal)
cd frontend
npm ci
npm run dev
```

The app works with **no API key**. It runs in Cached mode on 70 committed, recorded SerpApi responses.

| Variable | Default | Purpose |
|---|---|---|
| `SERPAPI_API_KEY` | none | Enables live searches |
| `MODE` | `cached` | `cached` or `live` |
| `LIVE_DAILY_CAP` | `200` | Daily live-search ceiling. When it's hit, requests fall back to cached |
| `SEARCH_TIMEOUT_SECONDS` | `8` | Per-search timeout. A failure becomes `unknown` |

```bash
cd backend && pytest             # 131 tests
cd frontend && npm test          # 8 tests
python evals/run_eval.py         # regenerates evals/report.md
```

### API

| Endpoint | Purpose |
|---|---|
| `POST /api/check` | Quick check |
| `POST /api/investigate` | Full-journey investigation |
| `GET /api/samples` | Demo samples (journey samples have `kind: "journey"`) |
| `GET /api/quota` | Live-search quota |
| `GET /api/health` | Health check and cache warm-up |

## Deploy

One Render web service, defined in `render.yaml`. Set `SERPAPI_API_KEY` in the Render dashboard. It is never stored in the repo.

## Project layout

```
backend/
  app/            main, pipeline, journey, registry, policy, privacy, extract,
                  fingerprint, verify_kit, serp, samples, checks/ (one file per check)
  fixtures/       recorded SerpApi responses
  evals/          labelled set, runner, report
  tests/
frontend/src/     components, OCR, API client
render.yaml
```

## Future work

Google Maps address check · self-hosted OCR assets · WhatsApp bot · placement-cell dashboard · forum-discussion signal · more real labelled offers.

---

<div align="center">

Built in one day for the **SerpApi India Hackathon 2026** by [Shyamanth Nadella](https://github.com/YOUR-USER).

*Never pay to get hired.*

</div>
