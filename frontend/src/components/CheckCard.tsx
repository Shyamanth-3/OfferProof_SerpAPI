import type { CheckResult, Evidence } from "../api";
import { STATUS_DOT } from "./VerdictBadge";

const domain = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
};
const hhmm = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });

const GROUPS: { kind: NonNullable<Evidence["kind"]>; title: string }[] = [
  { kind: "scam_report", title: "Scam reports" },
  { kind: "reused", title: "Same text, other names" },
  { kind: "official", title: "Company's own site" },
];

function EvidenceItem({ e }: { e: Evidence }) {
  return (
    <li className="min-w-0">
      <a href={e.url} target="_blank" rel="noreferrer noopener" className="block truncate text-[15px] text-fg underline underline-offset-4">
        {e.title}
      </a>
      <span className="meta text-faint">
        {domain(e.url)} · retrieved {hhmm(e.retrieved_at)}
        {e.from_cache && <span className="ml-2 rounded-full border border-line px-2 py-px">cached</span>}
      </span>
    </li>
  );
}

export function CheckCard({ check, delay, highlighted = false }: { check: CheckResult; delay: number; highlighted?: boolean }) {
  const s = check.status;
  return (
    <article
      id={`check-${check.id}`}
      className={`fade-up scroll-mt-24 rounded-[14px] border p-5 transition-colors ${highlighted ? "border-white" : "border-line"}`}
      style={{ animationDelay: `${delay}ms` }}
    >
      <header className="flex items-center gap-3">
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${STATUS_DOT[s]}`} aria-hidden="true" />
        <h3 className="m-0 text-[17px] font-medium">{check.title}</h3>
        <span className="sr-only">Status: {s}</span>
        {s === "info" && <span className="meta ml-auto rounded-full border border-blue/40 px-2.5 py-0.5 text-blue">context</span>}
        {s === "unknown" && <span className="meta ml-auto rounded-full border border-line px-2.5 py-0.5 text-dim">couldn't check</span>}
      </header>

      <p className="mt-3 mb-0 text-dim">{check.finding}</p>

      {check.phrases.length > 0 && (
        <div className="mt-4 flex flex-col gap-2">
          <span className="meta text-faint">Wording searched as an exact phrase:</span>
          {check.phrases.map((p) => (
            <q key={p} className="font-mono text-[12px] text-fg underline decoration-red decoration-1 underline-offset-4">
              {p}
            </q>
          ))}
        </div>
      )}

      {(check.engine || check.query) && (
        <div className="mt-4 flex flex-col gap-2">
          {check.engine && <span className="meta w-fit rounded-full border border-line px-2.5 py-0.5 text-dim">{check.engine}</span>}
          {check.query && (
            <code className="block rounded-[8px] bg-[#0c0c0c] px-3 py-2 font-mono text-[12px] break-words text-dim">{check.query}</code>
          )}
        </div>
      )}

      {check.id === "template_trace" && check.evidence.length > 0 && (
        <div className="mt-4 flex flex-col gap-4">
          {GROUPS.filter((g) => check.evidence.some((e) => e.kind === g.kind)).map((g) => (
            <div key={g.kind}>
              <h4 className="meta m-0 mb-2 font-medium text-dim">{g.title}</h4>
              <ul className="m-0 flex list-none flex-col gap-3 p-0">
                {check.evidence.filter((e) => e.kind === g.kind).slice(0, 3).map((e, i) => (
                  <EvidenceItem key={i} e={e} />
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}

      {check.id !== "template_trace" && check.evidence.length > 0 && (
        <ul className="m-0 mt-4 flex list-none flex-col gap-3 p-0">
          {check.evidence.slice(0, 3).map((e, i) => (
            <EvidenceItem key={i} e={e} />
          ))}
        </ul>
      )}
    </article>
  );
}
