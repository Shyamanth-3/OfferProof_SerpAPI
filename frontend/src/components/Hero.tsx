import { useState } from "react";
import { ScamDrum, type DrumWord } from "./ScamDrum";

const WORDS: DrumWord[] = [
  "REGISTRATION FEE", "TELEGRAM ONLY", "NO INTERVIEW", "PAY ₹1,999", "URGENT",
  "REFUNDABLE", "SELECTED!", "WORK FROM HOME", "LIMITED SEATS", "JOIN NOW",
].map((text) => ({ text }));

export function Hero() {
  const [playing, setPlaying] = useState(true);
  return (
    <section id="top" className="relative h-[100svh] min-h-[560px] overflow-hidden">
      <ScamDrum
        words={WORDS}
        speed={10}
        playing={playing}
        interactive
        fontSize="clamp(48px, 13vw, 200px)"
        className="absolute inset-0"
      />
      <div
        aria-hidden="true"
        className="pointer-events-none absolute inset-0"
        style={{ background: "radial-gradient(ellipse at center, transparent 30%, #111 92%)" }}
      />

      <div className="pointer-events-none absolute inset-0 flex flex-col justify-between p-4 sm:p-8">
        <div className="flex items-start justify-between gap-6">
          <div className="max-w-[34rem]">
            <h1 className="m-0 text-[44px] leading-none font-medium tracking-tight">Is this offer real?</h1>
            <p className="mt-4 mb-0 text-[17px] text-dim">
              Paste a job or internship offer. We trace it back to the company it claims to be.
            </p>
          </div>
          <span className="meta hidden shrink-0 text-dim sm:block">SerpApi · Google · News · Jobs</span>
        </div>

        <div className="relative flex items-end justify-between gap-4">
          <span className="meta font-medium">OfferProof</span>

          <a
            href="#check"
            className="pointer-events-auto absolute bottom-0 left-1/2 -translate-x-1/2 rounded-full bg-white px-6 py-3 text-[15px] font-medium whitespace-nowrap text-black no-underline"
          >
            Check an offer ↓
          </a>

          <div className="flex flex-col items-end gap-3">
            <button
              type="button"
              onClick={() => setPlaying((p) => !p)}
              aria-label={playing ? "Pause background animation" : "Play background animation"}
              className="pointer-events-auto grid h-9 w-9 cursor-pointer place-items-center rounded-full border border-line bg-transparent p-0 text-white"
            >
              {playing ? (
                <svg width="12" height="14" viewBox="0 0 12 14" fill="currentColor" aria-hidden="true">
                  <rect x="1" width="3.5" height="14" />
                  <rect x="7.5" width="3.5" height="14" />
                </svg>
              ) : (
                <svg width="12" height="14" viewBox="0 0 12 14" fill="currentColor" aria-hidden="true">
                  <path d="M1 0l11 7-11 7z" />
                </svg>
              )}
            </button>
            <a href="#how" className="meta pointer-events-auto text-fg underline underline-offset-4">
              How it works
            </a>
          </div>
        </div>
      </div>
    </section>
  );
}
