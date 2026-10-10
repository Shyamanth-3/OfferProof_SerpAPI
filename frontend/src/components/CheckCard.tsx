import type { CheckResult } from "../api";
import { STATUS_DOT } from "./VerdictBadge";

const domain = (url: string) => {
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
};
const hhmm = (iso: string) => new Date(iso).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hour12: false });

export function CheckCard({ check, delay }: { check: CheckResult; delay: number }) {
  const s = check.status;
  return (
    <article className="fade-up rounded-[14px] border border-line p-5" style={{ animationDelay: `${delay}ms` }}>
      <header className="flex items-center gap-3">
        <span className={`h-2.5 w-2.5 shrink-0 rounded-full ${STATUS_DOT[s]}`} aria-hidden="true" />
        <h3 className="m-0 text-[17px] font-medium">{check.title}</h3>
        <span className="sr-only">Status: {s}</span>
        {s === "info" && <span className="meta ml-auto rounded-full border border-blue/40 px-2.5 py-0.5 text-blue">context</span>}
        {s === "unknown" && <span className="meta ml-auto rounded-full border border-line px-2.5 py-0.5 text-dim">couldn't check</span>}
      </header>

      <p className="mt-3 mb-0 text-dim">{check.finding}</p>

      {(check.engine || check.query) && (
        <div className="mt-4 flex flex-col gap-2">
          {check.engine && <span className="meta w-fit rounded-full border border-line px-2.5 py-0.5 text-dim">{check.engine}</span>}
          {check.query && (
            <code className="block rounded-[8px] bg-[#0c0c0c] px-3 py-2 font-mono text-[12px] break-words text-dim">{check.query}</code>
          )}
        </div>
      )}

      {check.evidence.length > 0 && (
        <ul className="m-0 mt-4 flex list-none flex-col gap-3 p-0">
          {check.evidence.slice(0, 3).map((e, i) => (
            <li key={i} className="min-w-0">
              <a href={e.url} target="_blank" rel="noreferrer noopener" className="block truncate text-[15px] text-fg underline underline-offset-4">
                {e.title}
              </a>
              <span className="meta text-faint">
                {domain(e.url)} · retrieved {hhmm(e.retrieved_at)}
                {e.from_cache && <span className="ml-2 rounded-full border border-line px-2 py-px">cached</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}
