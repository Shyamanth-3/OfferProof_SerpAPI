import type { Status, Verdict } from "../api";

export const VERDICT_STYLE: Record<Verdict, { bg: string; word: string; color: string }> = {
  HIGH_RISK: { bg: "bg-red", word: "SCAM?", color: "var(--red)" },
  CAUTION: { bg: "bg-amber", word: "VERIFY", color: "var(--amber)" },
  NO_RED_FLAGS: { bg: "bg-green", word: "CLEAN", color: "var(--green)" },
  NOT_ENOUGH_EVIDENCE: { bg: "bg-grey", word: "UNSURE", color: "var(--grey)" },
};

export const STATUS_DOT: Record<Status, string> = {
  fail: "bg-red",
  warn: "bg-amber",
  info: "bg-blue",
  unknown: "bg-grey",
  pass: "bg-green",
};

export function VerdictBadge({ verdict, label }: { verdict: Verdict; label: string }) {
  return (
    <span className={`inline-block rounded-full px-5 py-2.5 text-[22px] leading-tight font-medium text-black ${VERDICT_STYLE[verdict].bg}`}>
      {label}
    </span>
  );
}
