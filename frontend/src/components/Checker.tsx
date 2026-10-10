import { useEffect, useRef, useState } from "react";
import { getQuota, getSamples, runCheck, type CheckResponse, type Mode, type Sample } from "../api";
import { Results } from "./Results";
import { ScamDrum, type DrumWord } from "./ScamDrum";
import { VERDICT_STYLE } from "./VerdictBadge";

const MAX = 10_000;
const MIN = 10; // matches the backend minimum
const MIN_SPIN_MS = 1100; // cached answers are instant; let the drum be seen
const LOADING_WORDS: DrumWord[] = ["CHECKING SENDER", "TRACING UPI", "COMPANY NOTICE", "JOB LISTINGS", "NEWS", "REGISTRY"].map((text) => ({ text }));

type Phase = "idle" | "loading" | "settling" | "done" | "error";

const inputCls =
  "w-full rounded-[14px] border border-line bg-raised px-4 py-3 font-sans text-[16px] text-fg placeholder:text-faint";

export function Checker() {
  const [samples, setSamples] = useState<Record<string, Sample>>({});
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
  const area = useRef<HTMLDivElement>(null);
  const detailsEl = useRef<HTMLDetailsElement>(null);
  const companyEl = useRef<HTMLInputElement>(null);

  const addCompany = () => {
    if (detailsEl.current) detailsEl.current.open = true;
    companyEl.current?.scrollIntoView({ behavior: "smooth", block: "center" });
    companyEl.current?.focus({ preventScroll: true });
  };

  useEffect(() => {
    getSamples().then(setSamples).catch(() => {});
  }, []);

  const submit = async () => {
    if (text.trim().length < MIN || phase === "loading" || phase === "settling") return;
    const t0 = Date.now();
    setPhase("loading");
    setResult(null);
    setError("");
    setRanMode(mode);
    area.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    try {
      const r = await runCheck({ offer_text: text, company: company.trim() || null, sender_email: sender.trim() || null, role: role.trim() || null }, mode);
      await new Promise((res) => setTimeout(res, Math.max(0, MIN_SPIN_MS - (Date.now() - t0))));
      setResult(r);
      setPhase("settling");
      if (mode === "live") getQuota("live").then((q) => setQuota(q.total_searches_left)).catch(() => {});
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
      setPhase("error");
    }
  };

  const busy = phase === "loading" || phase === "settling";
  const settleWord: DrumWord | null = result
    ? { text: VERDICT_STYLE[result.verdict].word, color: VERDICT_STYLE[result.verdict].color }
    : null;

  return (
    <section id="check" className="mx-auto w-full max-w-[980px] px-4 pt-24 pb-12">
      <h2 className="m-0 text-[27px] font-medium">Check an offer</h2>

      <div className="mt-6 flex flex-wrap gap-2" role="group" aria-label="Sample offers">
        {Object.entries(samples).map(([k, s]) => (
          <button
            key={k}
            type="button"
            onClick={() => {
              setText(s.offer_text);
              setCompany(s.company ?? "");
              setSender(s.sender_email ?? "");
              setRole(s.role ?? "");
              setFromChip(true);
            }}
            className="cursor-pointer rounded-full border border-line bg-transparent px-4 py-2 text-[14px] text-fg transition-colors hover:border-white"
          >
            {s.label}
          </button>
        ))}
      </div>

      <form
        className="mt-4"
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
      >
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
              if (fromChip) {
                // a sample's company/sender would silently override whatever the user pastes next
                setCompany("");
                setSender("");
                setRole("");
                setFromChip(false);
              }
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) submit();
            }}
            placeholder="Paste the full message here…"
            className={`${inputCls} min-h-[220px] resize-y pb-8`}
          />
          <span className="meta pointer-events-none absolute right-4 bottom-3 text-faint">
            {text.length.toLocaleString()} / {MAX.toLocaleString()}
          </span>
        </div>

        <details ref={detailsEl} className="mt-3" open={Boolean(company || sender || role) || undefined}>
          <summary className="meta cursor-pointer text-dim">Details (optional)</summary>
          <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-3">
            <input ref={companyEl} aria-label="Company" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Company" className={inputCls} />
            <input aria-label="Sender email" type="email" value={sender} onChange={(e) => setSender(e.target.value)} placeholder="Sender email" className={inputCls} />
            <input aria-label="Role" value={role} onChange={(e) => setRole(e.target.value)} placeholder="Role" className={inputCls} />
          </div>
        </details>

        <div className="mt-5 flex flex-wrap items-center gap-4">
          <button
            type="submit"
            disabled={text.trim().length < MIN || busy}
            className="cursor-pointer rounded-full border-0 bg-white px-7 py-3 text-[16px] font-medium text-black disabled:cursor-not-allowed disabled:opacity-40"
          >
            Check offer
          </button>
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
          <span className="meta text-dim">{mode === "cached" ? "Cached uses recorded searches" : "Live runs real searches"}</span>
        </div>
        <p className="meta mt-4 mb-0 text-faint">Aadhaar and PAN numbers are removed before anything is searched.</p>
        <p className="meta mt-1 mb-0 text-faint">Tip: include the subject line and sender. The company name is often only there.</p>
      </form>

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
            <button type="button" onClick={submit} className="mt-4 cursor-pointer rounded-full border border-white bg-transparent px-5 py-2 text-[14px] text-fg">
              Retry
            </button>
          </div>
        )}

        {phase === "done" && result && (
          <div className="mt-10">
            <Results r={result} quota={quota} mode={ranMode} onAddCompany={addCompany} />
          </div>
        )}
      </div>
    </section>
  );
}
