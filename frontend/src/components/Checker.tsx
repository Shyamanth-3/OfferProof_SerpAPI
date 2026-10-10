import { useEffect, useRef, useState } from "react";
import { detectOffer, getQuota, getSamples, runCheck, runJourney, type CheckResponse, type JourneyInput, type Mode, type Sample } from "../api";
import { applyDetected, describeAuto, NO_AUTO, type Auto, type Detected } from "../detect";
import { JourneyForm } from "./JourneyForm";
import { Results } from "./Results";
import { ScamDrum, type DrumWord } from "./ScamDrum";
import { VERDICT_STYLE } from "./VerdictBadge";
import { useScreenshot } from "../useScreenshot";

const MAX = 10_000;
const MIN = 10; // matches the backend minimum
const MIN_SPIN_MS = 1100; // cached answers are instant; let the drum be seen
const LOADING_WORDS: DrumWord[] = ["CHECKING SENDER", "TRACING UPI", "COMPANY NOTICE", "JOB LISTINGS", "NEWS", "REGISTRY"].map((text) => ({ text }));

type Phase = "idle" | "loading" | "settling" | "done" | "error";
type View = "quick" | "journey";

const inputCls =
  "w-full rounded-[14px] border border-line bg-raised px-4 py-3 font-sans text-[16px] text-fg placeholder:text-faint";

export function Checker() {
  const [samples, setSamples] = useState<Record<string, Sample>>({});
  const [view, setView] = useState<View>("quick");
  const [text, setText] = useState("");
  const [company, setCompany] = useState("");
  const [sender, setSender] = useState("");
  const [role, setRole] = useState("");
  const [mode, setMode] = useState<Mode>("cached");
  const [phase, setPhase] = useState<Phase>("idle");
  const [result, setResult] = useState<CheckResponse | null>(null);
  const [error, setError] = useState("");
  const [quota, setQuota] = useState<number | null>(null);
  const [ranMode, setRanMode] = useState<Mode>("cached");
  const [fromChip, setFromChip] = useState(false); // details were filled by a sample chip, not by the user
  const [detected, setDetected] = useState<Detected | null>(null); // what the backend found in the pasted text
  const [auto, setAuto] = useState<Auto>(NO_AUTO); // which fields hold an auto-detected value (not typed by the student)
  const area = useRef<HTMLDivElement>(null);
  const detailsEl = useRef<HTMLDetailsElement>(null);
  const companyEl = useRef<HTMLInputElement>(null);
  const retry = useRef<(() => void) | null>(null);

  const [dragging, setDragging] = useState(false);
  const fileInput = useRef<HTMLInputElement>(null);

  // any text edit (typing, OCR) drops chip-filled details: a sample's company/sender would silently override it
  const forgetChipDetails = () => {
    if (fromChip) {
      setCompany("");
      setSender("");
      setRole("");
      setAuto(NO_AUTO);
      setFromChip(false);
    }
  };
  const shot = useScreenshot((t) => {
    forgetChipDetails();
    setText((prev) => (prev.trim() ? `${prev}\n\n${t}` : t).slice(0, MAX)); // never overwrite what the user already typed
  });
  const imageFrom = (files?: FileList | null) => Array.from(files ?? []).find((f) => f.type.startsWith("image/"));

  const addCompany = () => {
    if (view === "journey") {
      const el = document.getElementById("journey-company");
      el?.scrollIntoView({ behavior: "smooth", block: "center" });
      return (el as HTMLInputElement | null)?.focus({ preventScroll: true });
    }
    if (detailsEl.current) detailsEl.current.open = true;
    companyEl.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    companyEl.current?.focus({ preventScroll: true });
  };

  useEffect(() => {
    getSamples().then(setSamples).catch(() => {});
  }, []);

  // As the text is pasted or typed, ask the backend what company, sender and role it contains (regex only, no search).
  useEffect(() => {
    if (text.trim().length < MIN) return setDetected(null);
    const ctl = new AbortController();
    const id = window.setTimeout(() => {
      detectOffer(text, ctl.signal).then(setDetected).catch(() => {}); // a convenience: if it fails, the student just types
    }, 450);
    return () => {
      window.clearTimeout(id);
      ctl.abort();
    };
  }, [text]);

  // Pre-fill the fields from it, but never over something the student typed or picked.
  useEffect(() => {
    const out = applyDetected({ company, sender, role }, auto, detected);
    setCompany(out.fields.company);
    setSender(out.fields.sender);
    setRole(out.fields.role);
    setAuto(out.auto);
  }, [detected]);

  const busy = phase === "loading" || phase === "settling";

  // one runner for both modes: shows the drum, waits a beat, lands on the verdict, keeps a retry
  const run = async (fn: () => Promise<CheckResponse>, m: Mode) => {
    const t0 = Date.now();
    retry.current = () => run(fn, m);
    setPhase("loading");
    setResult(null);
    setError("");
    setRanMode(m);
    area.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const r = await fn();
      await new Promise((res) => setTimeout(res, Math.max(0, MIN_SPIN_MS - (Date.now() - t0))));
      setResult(r);
      setPhase("settling");
      if (m === "live") getQuota("live").then((q) => setQuota(q.total_searches_left)).catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setPhase("error");
    }
  };

  const submit = () => {
    if (text.trim().length < MIN || busy) return;
    run(() => runCheck({ offer_text: text, company: company.trim() || null, sender_email: sender.trim() || null, role: role.trim() || null }, mode), mode);
  };
  const submitJourney = (input: JourneyInput) => {
    if (!busy) run(() => runJourney(input, mode), mode);
  };

  const switchView = (v: View) => {
    if (v === view) return;
    setView(v);
    setPhase("idle"); // a quick-check result doesn't belong under the journey form, and vice versa
    setResult(null);
  };

  const settleWord: DrumWord | null = result
    ? { text: VERDICT_STYLE[result.verdict].word, color: VERDICT_STYLE[result.verdict].color }
    : null;

  // ---- pieces shared by both modes ----
  const shotInput = (
    <input
      ref={fileInput}
      type="file"
      accept="image/png,image/jpeg,image/webp"
      className="sr-only"
      tabIndex={-1}
      aria-hidden="true"
      onChange={(e) => {
        const f = e.target.files?.[0];
        if (f) shot.start(f);
        e.target.value = ""; // allow picking the same file again
      }}
    />
  );
  const addShotButton = (
    <button
      type="button"
      onClick={() => fileInput.current?.click()}
      disabled={shot.s.reading}
      title="Read the text from a screenshot (PNG, JPG or WebP, up to 8 MB)"
      className="cursor-pointer rounded-full border border-dashed border-line bg-transparent px-4 py-2 text-[14px] text-fg transition-colors hover:border-white disabled:cursor-not-allowed disabled:opacity-40"
    >
      Add screenshot
    </button>
  );

  const shotPanel = (
    <>
      {(shot.s.reading || shot.s.thumb) && (
        <div className="mt-4 flex items-center gap-4 rounded-[14px] border border-line bg-raised p-3">
          {shot.s.thumb && <img src={shot.s.thumb} alt="Screenshot you added" className="h-16 w-16 shrink-0 rounded-[8px] object-cover" />}
          <div className="min-w-0 flex-1">
            {shot.s.reading ? (
              <>
                <p className="meta m-0 text-dim" role="status">
                  {shot.s.label}
                </p>
                <div
                  role="progressbar"
                  aria-label="Screenshot reading progress"
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-valuenow={shot.s.pct}
                  className="mt-2 h-1 overflow-hidden rounded-full bg-line"
                >
                  <div className="h-full bg-white transition-[width]" style={{ width: `${shot.s.pct}%` }} />
                </div>
              </>
            ) : (
              <p className="meta m-0 text-dim">Screenshot read. Its text is in the box below.</p>
            )}
          </div>
          <button type="button" onClick={shot.cancel} className="cursor-pointer rounded-full border border-line bg-transparent px-4 py-1.5 text-[13px] text-fg">
            {shot.s.reading ? "Cancel" : "Remove"}
          </button>
        </div>
      )}
      {shot.s.error && (
        <p role="alert" className="meta mt-3 mb-0 text-amber">
          {shot.s.error}
        </p>
      )}
    </>
  );

  const offerField = (
    <>
      <div className="relative">
        <label htmlFor="offer" className="sr-only">
          Offer message
        </label>
        <textarea
          id="offer"
          value={text}
          maxLength={MAX}
          onChange={(e) => {
            setText(e.target.value);
            forgetChipDetails();
            shot.clearReview();
          }}
          onPaste={(e) => {
            const f = imageFrom(e.clipboardData.files);
            if (f) {
              e.preventDefault(); // an image on the clipboard, not text
              shot.start(f);
            }
          }}
          onDragOver={(e) => {
            if (Array.from(e.dataTransfer.items).some((i) => i.kind === "file")) {
              e.preventDefault();
              setDragging(true);
            }
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            setDragging(false);
            const f = imageFrom(e.dataTransfer.files);
            if (f) {
              e.preventDefault();
              shot.start(f);
            }
          }}
          onKeyDown={(e) => {
            if (view === "quick" && e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit();
          }}
          placeholder="Paste the full message here, or drop or paste a screenshot of it…"
          className={`${inputCls} min-h-[220px] resize-y pb-8 ${dragging ? "border-white" : ""}`}
        />
        {dragging && (
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 grid place-items-center rounded-[14px] border-2 border-dashed border-white bg-bg/85 text-[17px] font-medium"
          >
            Drop the screenshot here to read its text
          </div>
        )}
        <span className="meta pointer-events-none absolute right-4 bottom-3 text-faint">
          {text.length.toLocaleString()} / {MAX.toLocaleString()}
        </span>
      </div>

      <p className="meta mt-2 mb-0 text-dim">
        <span aria-hidden="true">🖼 </span>
        Screenshots work too: drag one onto the box, paste it with Ctrl+V, or{" "}
        <button
          type="button"
          onClick={() => fileInput.current?.click()}
          disabled={shot.s.reading}
          className="cursor-pointer border-0 bg-transparent p-0 text-[13px] text-fg underline underline-offset-4 disabled:cursor-not-allowed disabled:opacity-40"
        >
          choose an image
        </button>
        . PNG, JPG or WebP, up to 8 MB.
      </p>

      {shot.s.review && (
        <p role="note" className="meta mt-2 mb-0 text-amber">
          Check the text before running — screenshot reading can make mistakes.
        </p>
      )}
    </>
  );

  const modeToggle = (
    <div role="radiogroup" aria-label="Search mode" className="flex rounded-full border border-line p-0.5">
      {(["cached", "live"] as Mode[]).map((m) => (
        <button
          key={m}
          type="button"
          role="radio"
          aria-checked={mode === m}
          onClick={() => setMode(m)}
          className={`cursor-pointer rounded-full border-0 px-4 py-1.5 text-[13px] capitalize ${mode === m ? "bg-white text-black" : "bg-transparent text-dim"}`}
        >
          {m}
        </button>
      ))}
    </div>
  );
  const modeNote = mode === "cached" ? "Cached uses recorded searches" : "Live runs real searches";

  return (
    <section id="check" className="mx-auto w-full max-w-[980px] px-4 pt-24 pb-12">
      {shotInput}
      <h2 className="m-0 text-[27px] font-medium">Check an offer</h2>

      <div role="radiogroup" aria-label="Check mode" className="mt-5 flex w-fit max-w-full flex-wrap rounded-[22px] border border-line p-0.5">
        {([["quick", "Quick check"], ["journey", "Investigate the full journey"]] as [View, string][]).map(([v, label]) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={view === v}
            onClick={() => switchView(v)}
            className={`cursor-pointer rounded-full border-0 px-5 py-2 text-[14px] ${view === v ? "bg-white text-black" : "bg-transparent text-dim"}`}
          >
            {label}
          </button>
        ))}
      </div>

      {view === "quick" ? (
        <>
          <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label="Sample offers">
            {Object.entries(samples)
              .filter(([, s]) => s.kind !== "journey")
              .map(([k, s]) => (
                <button
                  key={k}
                  type="button"
                  onClick={() => {
                    setText(s.offer_text ?? "");
                    setCompany(s.company ?? "");
                    setSender(s.sender_email ?? "");
                    setRole(s.role ?? "");
                    setAuto(NO_AUTO);
                    setFromChip(true);
                  }}
                  className="cursor-pointer rounded-full border border-line bg-transparent px-4 py-2 text-[14px] text-fg transition-colors hover:border-white"
                >
                  {s.label}
                </button>
              ))}
            {addShotButton}
          </div>

          {shotPanel}

          <form
            className="mt-4"
            onSubmit={(e) => {
              e.preventDefault();
              submit();
            }}
          >
            {offerField}

            <details ref={detailsEl} className="mt-3" open={Boolean(company || sender || role) || undefined}>
              <summary className="meta cursor-pointer text-dim">Details (optional)</summary>
              <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
                <input ref={companyEl} aria-label="Company" value={company} onChange={(e) => { setCompany(e.target.value); setAuto((a) => ({ ...a, company: false })); }} placeholder="Company" className={`${inputCls} ${auto.company ? "border-blue/60" : ""}`} />
                <input aria-label="Sender email" type="email" value={sender} onChange={(e) => { setSender(e.target.value); setAuto((a) => ({ ...a, sender: false })); }} placeholder="Sender email" className={`${inputCls} ${auto.sender ? "border-blue/60" : ""}`} />
                <input aria-label="Role" value={role} onChange={(e) => { setRole(e.target.value); setAuto((a) => ({ ...a, role: false })); }} placeholder="Role" className={`${inputCls} ${auto.role ? "border-blue/60" : ""}`} />
              </div>
              {(auto.company || auto.sender || auto.role) && (
                <p role="status" className="meta mt-2 mb-0 text-blue">
                  Detected from your message: {describeAuto(auto)}. Edit any field that is wrong.
                </p>
              )}
            </details>

            <div className="mt-5 flex flex-wrap items-center gap-4">
              <button
                type="submit"
                disabled={text.trim().length < MIN || busy}
                className="cursor-pointer rounded-full border-0 bg-white px-7 py-3 text-[16px] font-medium text-black disabled:cursor-not-allowed disabled:opacity-40"
              >
                Check offer
              </button>
              {modeToggle}
              <span className="meta text-dim">{modeNote}</span>
            </div>
            <p className="meta mt-4 mb-0 text-faint">Aadhaar and PAN numbers are removed before anything is searched.</p>
            <p className="meta mt-1 mb-0 text-faint">Your screenshot is read on this device and never uploaded.</p>
            <p className="meta mt-1 mb-0 text-faint">Tip: include the subject line and sender. The company name is often only there.</p>
          </form>
        </>
      ) : (
        <JourneyForm
          samples={Object.entries(samples).filter(([, s]) => s.kind === "journey")}
          offerSlot={
            <>
              {shotPanel}
              {offerField}
              <p className="meta m-0 text-faint">Your screenshot is read on this device and never uploaded.</p>
            </>
          }
          offerText={text}
          detected={detected}
          setOfferText={(t) => {
            setText(t);
            shot.clearReview();
          }}
          busy={busy}
          modeToggle={modeToggle}
          modeNote={modeNote}
          onSubmit={submitJourney}
        />
      )}

      <div ref={area} className="mt-14 scroll-mt-6">
        {phase !== "idle" && phase !== "error" && (
          <div className="flex flex-col items-center">
            <ScamDrum
              words={LOADING_WORDS}
              speed={120}
              fontSize="clamp(36px, 9vw, 84px)"
              className="relative h-[220px] w-full"
              settle={settleWord}
              onSettled={() => setPhase("done")}
            />
            <p className="meta mt-2 mb-0 text-dim" role="status">
              {phase === "loading" ? (ranMode === "live" ? "Running live searches…" : "Using recorded searches…") : "Done."}
            </p>
          </div>
        )}

        {phase === "error" && (
          <div role="alert" className="rounded-[14px] border border-line bg-raised p-5">
            <p className="m-0">We couldn't complete that check. {error}</p>
            <button type="button" onClick={() => retry.current?.()} className="mt-4 cursor-pointer rounded-full border border-white bg-transparent px-5 py-2 text-[14px] text-fg">
              Retry
            </button>
          </div>
        )}

        {phase === "done" && result && (
          <div className="mt-10">
            <Results r={result} quota={quota} mode={ranMode} onAddCompany={addCompany} onRetry={() => retry.current?.()} />
          </div>
        )}
      </div>
    </section>
  );
}
