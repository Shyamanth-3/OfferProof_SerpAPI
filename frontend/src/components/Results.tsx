import { useRef, useState } from "react";
import type { CheckResponse, JourneyResponse, Mode, Status } from "../api";
import { CheckCard } from "./CheckCard";
import { Timeline } from "./Timeline";
import { VerdictBadge } from "./VerdictBadge";
import { VerifyPanel } from "./VerifyPanel";

const ORDER: Status[] = ["fail", "warn", "info", "unknown", "pass"];

const Chip = ({ children, mono }: { children: React.ReactNode; mono?: boolean }) => (
  <span className={`rounded-full border border-line px-3 py-1 text-[13px] break-all ${mono ? "font-mono" : ""}`}>{children}</span>
);

export function Results({ r, quota, mode, onAddCompany, onRetry }: { r: CheckResponse | JourneyResponse; quota: number | null; mode: Mode; onAddCompany: () => void; onRetry: () => void }) {
  const slow = r.checks.filter((c) => c.skipped === "slow").length;
  const capped = r.checks.filter((c) => c.skipped === "capped").length;
  const journey = "timeline" in r ? r : null;
  const [highlight, setHighlight] = useState<string[]>([]);
  const clearTimer = useRef<number>(0);
  // clicking a timeline node scrolls to that stage's check cards and rings them for a moment
  const showChecks = (ids: string[]) => {
    const first = ids.map((id) => document.getElementById(`check-${id}`)).find(Boolean);
    first?.scrollIntoView({ behavior: "smooth", block: "center" });
    setHighlight(ids);
    window.clearTimeout(clearTimer.current);
    clearTimer.current = window.setTimeout(() => setHighlight([]), 2600);
  };
  const sorted = [...r.checks].sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status));
  const weighted = r.checks.filter((c) => c.weight > 0);
  const ran = weighted.filter((c) => c.scored).length;
  const { company, sender_email, role, identifiers: id } = r.extracted;
  const engines = [...new Set(r.checks.map((c) => c.engine).filter(Boolean))];
  const idChips = [...id.upi, ...id.phones, ...id.telegram.map((t) => `t.me/${t}`), ...id.links.filter((l) => !l.startsWith("t.me/"))];

  return (
    <div className="flex flex-col gap-10">
      <section className="fade-up flex flex-col gap-6" aria-live="polite">
        <div className="flex flex-wrap items-start justify-between gap-6">
          <div>
            <VerdictBadge verdict={r.verdict} label={r.verdict_label} />
            <p className="meta mt-3 mb-0 text-dim">Verdict decided by fixed rules, not AI.</p>
          </div>
          <div className="text-right">
            {r.risk_score !== null && <div className="text-[17px] font-medium">Risk {r.risk_score}/100</div>}
            <div className="meta group relative text-dim">
              Based on {ran} of {weighted.length} checks{" "}
              <span tabIndex={0} aria-label="Checks that couldn't run don't count for or against." className="cursor-help underline decoration-dotted">
                ({Math.round(r.coverage * 100)}% coverage)
              </span>
              <span
                role="tooltip"
                className="pointer-events-none absolute right-0 bottom-full z-10 mb-2 hidden w-60 rounded-[8px] border border-line bg-raised p-2 text-left text-[12px] text-fg group-focus-within:block group-hover:block"
              >
                Checks that couldn't run don't count for or against.
              </span>
            </div>
          </div>
        </div>

        {r.overrides.length > 0 && (
          <div className="border-l-2 border-red bg-raised px-5 py-4">
            <ul className="m-0 flex list-none flex-col gap-1 p-0">
              {r.overrides.map((o) => (
                <li key={o.rule}>{o.reason}</li>
              ))}
            </ul>
          </div>
        )}
      </section>

      {capped > 0 && (
        <div role="note" className="fade-up rounded-[14px] border border-amber/50 p-5">
          <p className="m-0 max-w-[40rem]">
            This site has reached its daily limit of live searches, so {capped === 1 ? "1 check was" : `${capped} checks were`} skipped. That says nothing about the offer. Try again tomorrow, or switch to Cached and use a sample offer.
          </p>
        </div>
      )}

      {slow > 0 && (
        <div role="note" className="fade-up flex flex-wrap items-center justify-between gap-4 rounded-[14px] border border-amber/50 p-5">
          <p className="m-0 max-w-[34rem]">
            {slow === 1 ? "1 check was" : `${slow} checks were`} skipped because a search was too slow. That says nothing about the offer. Checking again often works: searches that already finished aren't repeated.
          </p>
          <button type="button" onClick={onRetry} className="cursor-pointer rounded-full border border-white bg-transparent px-5 py-2 text-[14px] text-fg">
            Check again
          </button>
        </div>
      )}

      {journey && <Timeline nodes={journey.timeline} firstDivergence={journey.first_divergence} onSelect={showChecks} />}

      {!company && (
        <div role="note" className="fade-up flex flex-wrap items-center justify-between gap-4 rounded-[14px] border border-amber/50 p-5" style={{ animationDelay: "60ms" }}>
          <p className="m-0 max-w-[34rem]">
            We couldn't tell which company this offer claims to be from, so most checks didn't run. The name is often only in the subject line. Add it and check again.
          </p>
          <button type="button" onClick={onAddCompany} className="cursor-pointer rounded-full border border-white bg-transparent px-5 py-2 text-[14px] text-fg">
            Add company
          </button>
        </div>
      )}

      <section className="fade-up flex flex-col gap-3" style={{ animationDelay: "80ms" }}>
        <h2 className="m-0 text-[27px] font-medium">What we read</h2>
        <div className="flex flex-wrap gap-2">
          <Chip>Company: {company ?? "not found"}</Chip>
          <Chip>Sender: {sender_email ?? "none in message"}</Chip>
          <Chip>Role: {role ?? "not found"}</Chip>
          {idChips.map((c) => (
            <Chip key={c} mono>
              {c}
            </Chip>
          ))}
          {r.redacted.length > 0 && <Chip>Aadhaar/PAN removed</Chip>}
        </div>
        {r.extracted.fingerprint.length > 0 && (
          <div className="mt-1 flex flex-wrap items-center gap-2">
            <span className="meta text-faint">Fingerprint</span>
            {r.extracted.fingerprint.map((p) => (
              <span key={p} className="rounded-full border border-line px-3 py-1 font-mono text-[12px] break-words text-dim">
                “{p}”
              </span>
            ))}
          </div>
        )}
      </section>

      <section className="flex flex-col gap-4">
        <h2 className="m-0 text-[27px] font-medium">The checks</h2>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {sorted.map((c, i) => (
            <CheckCard key={c.id} check={c} delay={160 + i * 40} highlighted={highlight.includes(c.id)} />
          ))}
        </div>
      </section>

      {r.verify_kit && <VerifyPanel kit={r.verify_kit} />}

      <section className="fade-up rounded-[14px] border border-line p-6" style={{ animationDelay: "500ms" }}>
        <h2 className="m-0 text-[27px] font-medium">What to do next</h2>
        <ul className="mt-4 mb-0 flex list-disc flex-col gap-2 pl-5">
          {r.next_steps.map((s) => (
            <li key={s}>{s}</li>
          ))}
        </ul>
        {r.verdict === "HIGH_RISK" && (
          <div className="mt-6 flex flex-wrap gap-3">
            <a href="https://cybercrime.gov.in" target="_blank" rel="noreferrer noopener" className="rounded-full bg-red px-6 py-3 font-medium text-black no-underline">
              Report at cybercrime.gov.in
            </a>
            <a href="tel:1930" className="rounded-full border border-white px-6 py-3 font-medium text-fg no-underline">
              Call 1930
            </a>
          </div>
        )}
      </section>

      <p className="meta m-0 text-dim">
        SerpApi searches used: {r.searches_used} · engines: {engines.join(", ")} · {(r.elapsed_ms / 1000).toFixed(1)} s · {r.mode}
        {mode === "live" && quota !== null && ` · ${quota} searches left`}
      </p>
    </div>
  );
}
