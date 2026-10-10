# OfferProof — what the project does today

_State as of 2026-10-10. Backend and frontend are built, connected and tested. Deployment (`render.yaml`) and the README are still to do (see "Not done yet")._

## In one sentence

A student pastes a job or internship offer (or a screenshot of it); OfferProof checks whether it can be **traced back to the company it claims to be from**, shows every finding with its live-search source, and gives a verdict decided by **fixed rules, not AI**. There is no LLM anywhere in the project.

## The problem it targets

Fake offers on WhatsApp, Telegram and email, especially during placement season. Many impersonate real companies (TCS, Infosys, Wipro), so "is the company real?" is the wrong question. The right one is "did this offer really come from that company?" The tool also catches a second kind of trap: genuine-looking "internships" that are really paid courses sold with a job guarantee.

## How a check works

```
paste text / screenshot ─► 1 redact ─► 2 extract ─► 3 searches + rules (two stages, parallel) ─► 4 policy ─► verdict, evidence, verify kit
```

0. **Screenshot (optional).** Read on the device with OCR (see "Screenshot input"); the text lands in the box for the student to review. Only text ever reaches the backend.
1. **Redact.** Aadhaar and PAN numbers are replaced with `[REDACTED]` before anything else happens. Redacted text is the only text ever used or searched. (A `wa.me/91…` phone link is not mistaken for an Aadhaar.)
2. **Extract (regex only).** Company, sender email, role, and the identifiers a scammer leaves: UPI IDs, phone numbers (including `+91 98765 43210` style), Telegram handles, WhatsApp links, URLs. Also the **fingerprint**: 0–2 distinctive phrases that will be searched (see "Wording trace").
   - Company, in priority order: the field the user typed → a subject line like `Wipro | …` → "Greetings from X" / "on behalf of X" → the sender's domain name if repeated in the text (`careers@examplelearn.example` + "Examplelearn" ×3) → a bare "at X" / "from X" (ignores lists like "from MNCs, AWS & AICTE").
3. **Run the checks.** Stage 1 runs together (sender identity, impersonation news, job listing, registration, text red flags). Stage 2 needs the official domain from stage 1 (company fraud notice, payment-ID trace, wording trace, official careers page). Each check has an 8-second limit; any timeout or search failure becomes `unknown` and never crashes the request.
4. **Decide** with the policy below, then build the **verify kit**.

## The checks

| Check | Weight | Engine | What it asks |
|---|---|---|---|
| **Sender identity** (core) | 30 | Google | Is the sender's domain the company's **trusted** official domain? Free mail (Gmail…), a lookalike (`tcs-careers-india.in`), a hiring-platform domain, or just another domain? |
| **Message red flags** | 30 | none (rules) | See "Text red flags" below. |
| **Payment ID / contact trace** | 25 | Google | Is this UPI ID, phone, Telegram handle or off-domain sender publicly reported as a scam? |
| **Wording trace** | 20 | Google | Does the offer's own wording, searched as an exact phrase, appear in scam reports or on other sites under different names? |
| **Public job listing** | 10 | Google Jobs | Is *this role* at *this company* listed? A listing for a different role does not count. |
| **Company registration** | 5 | Google | Is the company on Zauba Corp / Tofler / TheCompanyCheck? |
| Company fraud notice | 0 (context) | Google `site:` | Does the company's own site warn about fake offers? |
| Official careers page | 0 (context) | Google `site:` | Where is the company's own careers page, and does it list this role? Only runs on a trusted domain. Never changes the score or verdict. |
| Brand impersonation context | 0 (context) | Google News | Is this brand often impersonated? Context only, never evidence against *this* offer. |

Total weight is **120**, computed from the registered checks (`app/registry.py`), and coverage is scored weight ÷ 120.

Statuses are `pass`, `warn`, `fail`, `info` (shown, never scored) and `unknown` (shown, never scored; explains why).

**Trusted vs untrusted official domain.** The official domain is found with a Google search for "{company} official website". A domain is *trusted* only if it comes from Google's knowledge-panel website or from a built-in list of about 20 big recruiters (TCS, Infosys, Wipro, HCL, Cognizant, Accenture, Amazon, Zoho…) with their accepted mail domains. A domain that is only the top search result is *untrusted*: a sender matching it gets a **warning, never a pass**, and it is never shown to students as "official" (a scam's own site can rank first).

**Lookalike detection** is conservative: same name with another ending (`tcs.in`), the brand as a hyphen-separated word (`tcs-careers-india.in`), brand plus extra words (`infosysrecruitment.com`), a brand inside a longer host (`tcs.com.evil.in`), or a small edit distance for names of 5+ letters. Short names like `hcl` never fuzzy-match `tcs`.

### Text red flags (no API)

Matching handles negation within the same clause ("We never charge any registration fee" does not fire), Hinglish ("registration charge jama karo"), and ignores bare "pay", "payroll", "stipend will be paid".

- **Hard flags:** `FEE` (registration/training/security fee, "pay ₹…", any UPI ID, Hinglish fee phrases), `OFF_PLATFORM` (t.me, wa.me, "contact HR on Telegram"), `NO_INTERVIEW`, `URGENCY`, `UNREALISTIC_PAY`, `TASK_SCAM`, `JOB_GUARANTEE` ("100% job guarantee", "guaranteed placements"), `APPLY_VIA_FORM` (application through forms.gle / Google Forms / Typeform / bit.ly and similar).
- **Soft flags (warning only, never escalate alone):** `FEES_UNSTATED` ("applicable fees"), `TRAINING_FIRST` (training phase plus a stipend that only comes later), `COURSE_SELLING` ("Enroll Now").
- **Status:** any `FEE` → fail; two or more other hard flags → fail; one hard flag or any soft flag → warn; none → pass. Findings are written in plain English.

### Wording trace (the "template" insight)

Fake offers are mass-produced templates, so the same distinctive paragraph is reused under different company names. `app/fingerprint.py` (pure, no network) picks up to two phrases of 8–12 words: it splits sentences with the same clause-safe splitter as the red-flag rules, strips everything specific to the recipient or company (emails, URLs, phones, UPI IDs, amounts, dates, greeting names, the company name, the sender's domain), rejects short, stopword-heavy or generic-HR sentences, and never builds a phrase across a removed span. `checks/template_trace.py` searches each phrase in quotes and keeps a result only if it really contains ≥60% of the phrase's words:

| Result | Meaning | Status |
|---|---|---|
| Scam keywords in the snippet, or a known complaint site | scam report | **fail** (and override `TEMPLATE_REPORTED`) |
| ≥2 distinct non-job-board sites using the text under other names, no official hit | reused text | warn (score only) |
| Trusted official domain contains the text | company's own wording | pass |
| Otherwise, or no phrase could be chosen | — | unknown ("not evidence either way") |

Job boards (Internshala, Indeed, Naukri, LinkedIn…) are ignored for the "reused" test: they list real roles for everyone, so a role-title phrase always matches them. (This was found in the first real run, where a generic "work from home data entry internship" phrase produced a false "mass-produced" warning, and fixed.)

**Honest result so far:** on the 8 labelled offers, no real-received offer produced a warning or failure. Email and WhatsApp text is rarely indexed by Google, so this check can only help when scam wording has been quoted somewhere public. That is why there is no template-scam demo sample.

## The verdict (fixed rules)

- Each scored check adds 0 (pass), 0.5 × weight (warn) or 1 × weight (fail). `info` and `unknown` are left out of both the score and the denominator.
- `risk_score` = points ÷ scored weight × 100. `coverage` = scored weight ÷ 120.
- Base verdict: coverage under 50% → **Not enough evidence** (never "No red flags"); otherwise score ≥ 55 → **High risk**, ≥ 25 → **Caution**, else **No red flags**.
- **Overrides** can only raise severity, and all that apply are shown:

| Override | Raises to | Trigger |
|---|---|---|
| `FEE_DEMANDED` | High risk | Any fee demanded |
| `LOOKALIKE_DOMAIN` | High risk | Sender domain imitates the official one |
| `IDENTIFIER_REPORTED` | High risk | A payment ID or number is publicly reported as a scam |
| `TEMPLATE_REPORTED` | High risk | The offer's wording matches text reported as a scam elsewhere |
| `FREE_MAIL_SENDER` | Caution (High if the company warns about fakes) | Free mail while an official domain exists |
| `OFF_PLATFORM_ONLY` | Caution | Telegram/WhatsApp push and no official-domain sender |
| `THIRD_PARTY_SENDER` | Caution | Known big brand, sent from a different non-free, non-platform domain |
| `JOB_GUARANTEE` | Caution | "No genuine employer can guarantee you a job" |

- **It never says "safe."** The best result is "No red flags found — still, never pay to get hired." High risk adds cybercrime.gov.in and the 1930 helpline. The "official careers page" suggestion appears only when the domain is trusted.

## Verify it yourself (the kit)

`app/verify_kit.py` (pure, nothing generated) returns, for every check:
- a **fixed message** the student can send to the company: "Hello, I received a job offer that claims to be from {company} for the role of {role}. It was sent by {sender}[, and it asks for a payment of ₹{amount}][ to the UPI ID {upi}]. Could you please confirm whether this offer is genuine? Thank you." It never contains the student's name, phone, email, Aadhaar or PAN, and never a link or phone number. It quotes the sender's address and any UPI ID as plain text so the company can recognise the mail.
- the **official careers URL** and whether the role is listed there, and a **`mailto:`** link with a subject and the message as the body but **no recipient** (the student takes the address from the official site).
- **Hard rule:** every linkable or actionable field comes only from the *trusted* official domain. With an untrusted domain there is no careers link and no mailto, and the advice says to look the company up yourself. This is covered by tests.

## What the user sees (frontend)

Dark single page (Vite + React + TypeScript + Tailwind v4, no UI or animation library):

- **Hero:** a 3D rotating drum of giant red scam phrases (CSS 3D + `requestAnimationFrame`, pauses off-screen, play/pause button, static under reduced motion).
- **Checker:** textarea, sample chips, **Add screenshot**, optional details (company, sender, role), Cached/Live toggle. Chip-filled details are cleared when you type your own text so they can't silently override it.
- **While checking:** a compact drum spins, then lands on SCAM? / VERIFY / CLEAN / UNSURE.
- **Result:** verdict badge, "decided by fixed rules, not AI", risk score and coverage, override banner, "What we read" (including the **Fingerprint** phrases), one card per check (status, finding, engine, exact query, up to 3 evidence links with retrieval time; the wording-trace card quotes the searched phrase and groups results as Scam reports / Same text, other names / Company's own site), the **Verify it yourself** panel (open careers page, copy message, email the company, "Role listed on official site ✓"), next steps. If no company was found, a prompt with an "Add company" button.
- **Footer strip:** searches used, engines, time, mode, and remaining SerpApi quota in Live mode.

### Screenshot input (on-device OCR)

- Add a PNG/JPG/WebP (max 8 MB) with the button, by dragging onto the textarea, or by pasting an image (Ctrl+V). `tesseract.js` v5 is loaded with a dynamic `import()` only when an image is added, so the main bundle stays small.
- The image is scaled 2× if narrow, turned to grayscale with mild contrast, and **inverted automatically for dark-mode chats**. Progress and a Cancel button are shown.
- The text is cleaned (timestamps, read-receipt ticks, "Forwarded" labels removed; wrapped lines merged), placed in the textarea, **never auto-submitted**, with the note "Check the text before running — screenshot reading can make mistakes."
- **Privacy:** "Your screenshot is read on this device and never uploaded." This is true: no image bytes go to the backend (verified by watching the network). One nuance: on first use the browser downloads the OCR engine and English language data from the public CDN `cdn.jsdelivr.net`. Self-hosting those files is a possible later step.

## Architecture and files

```
OfferProof/
├── backend/            FastAPI (Python 3.11), serves the built frontend too
│   ├── app/            main, pipeline, registry, models, privacy, extract, fingerprint, serp, policy, verify_kit, samples
│   │   └── checks/     one module per check
│   ├── fixtures/       56 recorded SerpApi responses (committed) so Cached mode works offline
│   ├── cache/          live-search disk cache (git-ignored)
│   ├── scripts/        record_fixtures.py (records only searches missing from fixtures/; asks first; --yes skips)
│   ├── evals/          labeled.jsonl (real-received + synthetic), run_eval.py, report.md
│   └── tests/          81 tests
└── frontend/           Vite + React + TS + Tailwind v4 (dist/ is served by the backend)
    └── src/            components/, ocr.ts, ocrClean.ts (+ test), useScreenshot.ts, api.ts
```

- **API:** `POST /api/check?mode=live|cached`, `GET /api/samples`, `GET /api/quota`, `GET /api/health`. The response only ever gained fields (`verify_kit`, `extracted.fingerprint`, `phrases`, `evidence[].kind`); nothing was renamed or removed.
- **Search layer:** SerpApi official client; disk cache; fixtures; per-request call counter; "no results" treated as a valid empty answer.
- **Searches per offer:** sender 1, impersonation news 1, job listing 1, registration 1, fraud notice 1 (needs an official domain), payment-ID trace 0–3, wording trace 0–2, careers page 1 (trusted domain only). Typically 6–8, **at most 11**.
- **Quota protection:** live searches capped per day (`LIVE_DAILY_CAP`, default 200); offer text limited to 10,000 characters; per-search timeout `SEARCH_TIMEOUT_SECONDS` (default 8).
- **Config (`backend/.env`):** `SERPAPI_API_KEY`, `MODE` (`cached` default or `live`), `LIVE_DAILY_CAP`, `SEARCH_TIMEOUT_SECONDS`. The file is git-ignored.
- **Git:** the repo is initialised, with one commit per build step.

**Run it:**
```
cd frontend; npm run build
cd ..\backend; .venv\Scripts\python -m uvicorn app.main:app --port 8000      # then open http://localhost:8000
```
Frontend development with hot reload: `npm run dev` in `frontend/` (port 5173, proxies `/api` to 8000). Tests: `.venv\Scripts\python -m pytest` in `backend/`, and `npm test` in `frontend/` (the OCR clean-up, via Node's built-in runner).
Adding a sample or eval row: `.venv\Scripts\python -m scripts.record_fixtures` shows how many new searches it needs and asks before spending any.

## How it has been verified

- **81 backend tests** and **8 frontend tests** pass, with no network: unit tests (negation, Hinglish, lookalikes, privacy, policy, extraction, phrase selection, classification, verify kit), the 5 acceptance samples against recorded searches, and regression tests built from real emails that slipped through. They also pass with the local `cache/` hidden, so a fresh clone reproduces everything from the committed fixtures.
- **Browser checks** (Edge, scripted) at 375, 768 and 1280 px: every sample chip, the verify-kit buttons (copy, mailto, careers link), a screenshot upload by picker, paste and drag-drop (a WhatsApp-style image we rendered ourselves, light and dark, not a real chat), cancel, bad type, too big, error and Retry, pause and reduced motion.
- **Eval (cached, fixtures only).** Real-received: 2 offers, scam recall 1/1, strict 0/1, no genuine rows yet. Synthetic: 6 offers, scam recall 3/3, strict 3/3, false-alarm rate 0/2. Combined: scam recall 4/4, strict 3/4, false-alarm rate 0/2. This is a smoke test, not accuracy; the report says so.

## Honest limits

- **Tiny labelled set.** 8 offers (2 real) is not evidence of accuracy. Real labelled offers are needed (aim for 30+).
- **Regex extraction.** English and Hinglish only. If the company name is not in the text (often only in the email subject), most checks can't run; the tool says so instead of guessing.
- **Absence of reports is not proof of safety.** "No public reports found" is shown as unknown, never as a pass.
- **Wording trace can't fingerprint short or very generic messages**, and exact-phrase search only finds text Google has indexed. Most email and WhatsApp text isn't, so a clean result there means nothing.
- **OCR quality depends on the screenshot.** Blurry, tiny or heavily styled screenshots read badly; the student must check the text before running.
- **It checks traceability, not intent.** A genuine company's own mail with a misleading pitch is caught only by the text rules (job guarantee, fees, form links).
- **Small companies often have no findable official site**, so the sender check stays "unknown" for them, and for an unconfirmed site it is only a warning.
- **Third-party hosting of OCR assets:** the OCR engine and language data come from `cdn.jsdelivr.net` on first use.
- **Not legal advice.**

## Not done yet

1. **`render.yaml` and the README** (problem, demo GIF, ASCII flow, engines used, privacy, embedded accuracy report, limitations, future work).
2. **More real labelled offers** for the eval, ideally with some genuine ones; none of the real rows is genuine yet.
3. **GitHub link** in the footer (currently a placeholder).
4. **Self-host the OCR assets** instead of loading them from a CDN.
5. **Future ideas:** a WhatsApp bot, a placement-cell dashboard, a moderated reporting channel.
