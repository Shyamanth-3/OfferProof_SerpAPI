# OfferProof — what the project does today

_State as of 2026-10-10. Backend and frontend are built, connected and tested. Deployment and the README are still to do (see "Not done yet")._

## In one sentence

A student pastes a job or internship offer; OfferProof checks whether it can be **traced back to the company it claims to be from**, shows every finding with its live-search source, and gives a verdict decided by **fixed rules, not AI**.

## The problem it targets

Fake offers on WhatsApp, Telegram and email, especially during placement season. Many impersonate real companies (TCS, Infosys, Wipro), so "is the company real?" is the wrong question. The right one is "did this offer really come from that company?" The tool also catches a second kind of trap: genuine-looking "internships" that are really paid courses sold with a job guarantee.

## How a check works

```
paste offer ─► 1 redact ─► 2 extract ─► 3 search + rules (parallel) ─► 4 policy ─► verdict + evidence
```

1. **Redact.** Aadhaar and PAN numbers are replaced with `[REDACTED]` before anything else happens. Redacted text is the only text ever used or searched. (A `wa.me/91…` phone link is not mistaken for an Aadhaar.)
2. **Extract (regex only).** Company, sender email, role, and the identifiers a scammer leaves: UPI IDs, phone numbers (including `+91 98765 43210` style), Telegram handles, WhatsApp links, URLs.
   - Company, in priority order: the field the user typed → a subject line like `Wipro | …` → "Greetings from X" / "on behalf of X" → the sender's domain name if repeated in the text (`careers@examplelearn.example` + "Examplelearn" ×3) → a bare "at X" / "from X" (ignores lists like "from MNCs, AWS & AICTE").
3. **Run the checks.** Stage 1 runs together (sender identity, impersonation news, job listing, registration, text red flags). Stage 2 needs the official domain from stage 1 (company fraud notice, identifier trace). Each check has an 8-second limit; any timeout or search failure becomes `unknown` and never crashes the request.
4. **Decide** with the policy below.

## The checks

| Check | Weight | Engine | What it asks |
|---|---|---|---|
| **Sender identity** (core) | 30 | Google | Is the sender's domain the company's official domain? Free mail (Gmail…), a lookalike (`tcs-careers-india.in`), a hiring-platform domain, or just another domain? |
| **Payment ID / contact trace** | 25 | Google | Is this UPI ID, phone, Telegram handle or off-domain sender publicly reported as a scam? |
| **Message red flags** | 30 | none (rules) | See "Text red flags" below. |
| **Public job listing** | 10 | Google Jobs | Is *this role* at *this company* listed? A listing for a different role does not count. |
| **Company registration** | 5 | Google | Is the company on Zauba Corp / Tofler / TheCompanyCheck? |
| Company fraud notice | 0 (context) | Google `site:` | Does the company's own site warn about fake offers? |
| Brand impersonation context | 0 (context) | Google News | Is this brand often impersonated? Context only, never evidence against *this* offer. |

Statuses are `pass`, `warn`, `fail`, `info` (shown, never scored) and `unknown` (shown, never scored; explains why).

**How the official domain is found.** A Google search for "{company} official website". Google's knowledge-panel website, or a built-in list of about 20 big recruiters (TCS, Infosys, Wipro, HCL, Cognizant, Accenture, Amazon, Zoho…) with their accepted mail domains, is treated as *trusted*. A domain that is only the top search result is used for comparison but never shown to students as "official", because a scam's own site can rank first.

**Lookalike detection** is conservative: same name with another ending (`tcs.in`), the brand as a hyphen-separated word (`tcs-careers-india.in`), brand plus extra words (`infosysrecruitment.com`), a brand inside a longer host (`tcs.com.evil.in`), or a small edit distance for names of 5+ letters. Short names like `hcl` never fuzzy-match `tcs`.

### Text red flags (no API)

Matching handles negation within the same clause ("We never charge any registration fee" does not fire), Hinglish ("registration charge jama karo"), and ignores bare "pay", "payroll", "stipend will be paid".

- **Hard flags:** `FEE` (registration/training/security fee, "pay ₹…", any UPI ID, Hinglish fee phrases), `OFF_PLATFORM` (t.me, wa.me, "contact HR on Telegram"), `NO_INTERVIEW`, `URGENCY`, `UNREALISTIC_PAY`, `TASK_SCAM`, `JOB_GUARANTEE` ("100% job guarantee", "guaranteed placements"), `APPLY_VIA_FORM` (application through forms.gle / Google Forms / Typeform / bit.ly and similar).
- **Soft flags (warning only, never escalate alone):** `FEES_UNSTATED` ("applicable fees"), `TRAINING_FIRST` (training phase plus a stipend that only comes later), `COURSE_SELLING` ("Enroll Now").
- **Status:** any `FEE` → fail; two or more other hard flags → fail; one hard flag or any soft flag → warn; none → pass.

## The verdict (fixed rules)

- Each scored check adds 0 (pass), 0.5 × weight (warn) or 1 × weight (fail). `info` and `unknown` are left out of both the score and the denominator.
- `risk_score` = points ÷ scored weight × 100. `coverage` = scored weight ÷ 100.
- Base verdict: coverage under 50% → **Not enough evidence** (never "No red flags"); otherwise score ≥ 55 → **High risk**, ≥ 25 → **Caution**, else **No red flags**.
- **Overrides** can only raise severity, and all that apply are shown:

| Override | Raises to | Trigger |
|---|---|---|
| `FEE_DEMANDED` | High risk | Any fee demanded |
| `LOOKALIKE_DOMAIN` | High risk | Sender domain imitates the official one |
| `IDENTIFIER_REPORTED` | High risk | A payment ID or number is publicly reported as a scam |
| `FREE_MAIL_SENDER` | Caution (High if the company warns about fakes) | Free mail while an official domain exists |
| `OFF_PLATFORM_ONLY` | Caution | Telegram/WhatsApp push and no official-domain sender |
| `THIRD_PARTY_SENDER` | Caution | Known big brand, sent from a different non-free, non-platform domain |
| `JOB_GUARANTEE` | Caution | "No genuine employer can guarantee you a job" |

- **It never says "safe."** The best result is "No red flags found — still, never pay to get hired." High risk adds cybercrime.gov.in and the 1930 helpline. The official-careers-page suggestion appears only when the domain is trusted.

## What the user sees (frontend)

Dark single page (Vite + React + TypeScript + Tailwind v4, no UI or animation library):

- **Hero:** a 3D rotating drum of giant red scam phrases (CSS 3D + `requestAnimationFrame`, pauses off-screen, play/pause button, static under reduced motion).
- **Checker:** textarea, sample chips, optional details (company, sender, role), Cached/Live toggle. Chip-filled details are cleared when you type your own text so they can't silently override it.
- **While checking:** a compact drum spins, then lands on SCAM? / VERIFY / CLEAN / UNSURE.
- **Result:** verdict badge, "decided by fixed rules, not AI", risk score and coverage, override banner, "What we read", one card per check (status, finding, engine, exact query, up to 3 evidence links with retrieval time), next steps. If no company was found, a prompt with an "Add company" button.
- **Footer strip:** searches used, engines, time, mode, and remaining SerpApi quota in Live mode.

## Architecture and files

```
OfferProof/
├── backend/            FastAPI (Python 3.11), serves the built frontend too
│   ├── app/            main, pipeline, models, privacy, extract, serp, policy, samples
│   │   └── checks/     one module per check
│   ├── fixtures/       30 recorded SerpApi responses (committed) so Cached mode works offline
│   ├── cache/          live-search disk cache (git-ignored)
│   ├── scripts/        record_fixtures.py (20s timeout, copies late responses too)
│   ├── evals/          labeled.jsonl, run_eval.py, report.md
│   └── tests/          45 tests
└── frontend/           Vite + React + TS + Tailwind v4 (dist/ is served by the backend)
```

- **API:** `POST /api/check?mode=live|cached`, `GET /api/samples`, `GET /api/quota`, `GET /api/health`.
- **Search layer:** SerpApi official client; disk cache; fixtures; per-request call counter; "no results" treated as a valid empty answer.
- **Quota protection:** live searches capped per day (`LIVE_DAILY_CAP`, default 200); offer text limited to 10,000 characters; per-search timeout `SEARCH_TIMEOUT_SECONDS` (default 8).
- **Config (`backend/.env`):** `SERPAPI_API_KEY`, `MODE` (`cached` default or `live`), `LIVE_DAILY_CAP`, `SEARCH_TIMEOUT_SECONDS`. The file is git-ignored.

**Run it:**
```
cd frontend; npm run build
cd ..\backend; .venv\Scripts\python -m uvicorn app.main:app --port 8000      # then open http://localhost:8000
```
Frontend development with hot reload: `npm run dev` in `frontend/` (port 5173, proxies `/api` to 8000). Tests: `.venv\Scripts\python -m pytest` in `backend/`.

## How it has been verified

- **45 automated tests** pass, with no network: unit tests (negation, Hinglish, lookalikes, privacy, policy, extraction), the 5 acceptance samples against recorded searches, and regression tests built from real emails that slipped through (Wipro-style third-party program, Examplelearn-style paid course, a fee scam pointing at an untrusted site).
- **Browser checks** (Edge, scripted) on the 5 sample chips, 375/768/1280 px widths, error and retry, pause and reduced motion.
- **Eval on the 5 seed offers** (cached): scam recall 2/2, false-alarm rate 0/2. This is a smoke test, not accuracy; the report says so.

## Honest limits

- **Tiny labelled set.** 5 offers is not evidence of accuracy. Real labelled offers are needed (aim for 20+, ideally 30+).
- **Regex extraction.** English and Hinglish only. If the company name is not in the text (often only in the email subject), most checks can't run; the tool says so instead of guessing.
- **Absence of reports is not proof of safety.** "No public reports found" is shown as unknown, never as a pass.
- **It checks traceability, not intent.** A genuine company's own mail with a misleading pitch is caught only by the text rules (job guarantee, fees, form links).
- **A spoofed-but-plausible domain can still pass.** If a scammer's own website ranks first for the company name and the sender uses it, the sender check can pass. Planned fix below.
- **Small companies often have no findable official site**, so the sender check stays "unknown" for them.
- **Not legal advice.**

## Not done yet

1. **Careers-site check:** `site:{official domain}` search for the role (confidence boost only, never a fail). Needs fixtures re-recorded.
2. **Tighten the sender check:** require a trusted official domain before the sender can pass; an unverified match becomes a warning.
3. **"Verify it yourself" kit:** official careers URL plus a ready-to-send message to the company's HR (no AI verdicts).
4. **`render.yaml` and the README** (problem, demo GIF, ASCII flow, engines used, privacy, embedded accuracy report, limitations, future work).
5. **Real labelled eval set** and a re-run of the eval.
6. **GitHub link** in the footer (currently a placeholder).
7. **Future ideas:** screenshot OCR, a WhatsApp bot, a placement-cell dashboard, a moderated reporting channel.
