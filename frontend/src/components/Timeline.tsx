import type { TimelineNode, TimelineStage } from "../api";

const LABEL: Record<TimelineStage, string> = {
  listing: "Listing",
  recruiter: "Recruiter",
  interview: "Interview",
  payment: "Payment",
  offer: "Offer",
};
// colour AND a word, so the status never relies on colour alone
const STATUS: Record<TimelineNode["status"], { word: string; dot: string; text: string }> = {
  matches: { word: "Matches", dot: "bg-green border-green", text: "text-green" },
  diverges: { word: "Diverges", dot: "bg-red border-red", text: "text-red" },
  unverified: { word: "Unverified", dot: "bg-grey border-grey", text: "text-grey" },
  not_provided: { word: "Not provided", dot: "bg-transparent border-faint", text: "text-faint" },
};

export function Timeline({ nodes, firstDivergence, onSelect }: {
  nodes: TimelineNode[];
  firstDivergence: { stage: string; reason: string } | null;
  onSelect: (ids: string[]) => void;
}) {
  return (
    <section aria-labelledby="journey-title" className="fade-up flex flex-col gap-5" style={{ animationDelay: "60ms" }}>
      <h2 id="journey-title" className="m-0 text-[27px] font-medium">
        The journey
      </h2>

      <ol className="m-0 flex list-none flex-col p-0 md:grid md:grid-cols-5">
        {nodes.map((n, i) => {
          const s = STATUS[n.status];
          const first = firstDivergence?.stage === n.stage;
          return (
            <li key={n.stage} className="relative flex gap-4 pb-6 last:pb-0 md:block md:pb-0 md:pr-3">
              {/* connector: vertical on mobile, horizontal on desktop */}
              {i < nodes.length - 1 && (
                <>
                  <span aria-hidden="true" className="absolute top-8 left-[11px] h-[calc(100%-1rem)] w-px bg-line md:hidden" />
                  <span aria-hidden="true" className="absolute top-[11px] left-8 hidden h-px w-[calc(100%-2rem)] bg-line md:block" />
                </>
              )}
              <span
                aria-hidden="true"
                className={`relative z-10 mt-0.5 grid h-[23px] w-[23px] shrink-0 place-items-center rounded-full border-2 ${s.dot} ${first ? "outline-2 outline-offset-4 outline-red" : ""}`}
              />
              <button
                type="button"
                onClick={() => onSelect(n.check_ids)}
                aria-label={`${LABEL[n.stage]}: ${s.word}. ${n.headline}. Show its checks.`}
                className="min-w-0 flex-1 cursor-pointer border-0 bg-transparent p-0 text-left text-fg md:mt-3"
              >
                <span className="block text-[17px] font-medium">{LABEL[n.stage]}</span>
                <span className={`meta block ${s.text}`}>
                  {first && "▲ "}
                  {s.word}
                </span>
                <span className="mt-1 block text-[14px] leading-snug text-dim">{n.headline}</span>
              </button>
            </li>
          );
        })}
      </ol>

      {firstDivergence ? (
        <div role="note" className="border-l-2 border-red bg-raised px-5 py-4">
          <p className="m-0 font-medium">Your journey left the company's real process here:</p>
          <p className="m-0 mt-1">
            <span className="meta mr-2 rounded-full border border-red/60 px-2.5 py-0.5 text-red">{LABEL[firstDivergence.stage as TimelineStage] ?? firstDivergence.stage}</span>
            {firstDivergence.reason}
          </p>
        </div>
      ) : (
        <p className="meta m-0 text-dim">We found no point where this journey leaves the company's real process, from what you told us. That is not a guarantee.</p>
      )}
    </section>
  );
}
