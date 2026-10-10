const STEPS = [
  ["Redact", "Aadhaar/PAN removed."],
  ["Extract", "Company, sender, UPI, phone, Telegram."],
  ["Search", "Parallel SerpApi checks across Google, News and Jobs."],
  ["Decide", "Fixed rules with hard overrides. Evidence is cited, and nothing is ever called “safe”."],
];

export function HowItWorks() {
  return (
    <section id="how" className="mx-auto w-full max-w-[980px] scroll-mt-6 px-4 py-24">
      <h2 className="m-0 text-[27px] font-medium">How it works</h2>
      <ol className="m-0 mt-8 grid list-none grid-cols-1 gap-8 p-0 md:grid-cols-4 md:gap-6">
        {STEPS.map(([title, line], i) => (
          <li key={title} className="border-t border-line pt-4">
            <span className="meta text-faint">0{i + 1}</span>
            <h3 className="mt-2 mb-1 text-[17px] font-medium">{title}</h3>
            <p className="m-0 text-[15px] text-dim">{line}</p>
          </li>
        ))}
      </ol>
      <p className="mt-12 mb-0 text-dim">Built for students. Never pay to get hired.</p>
    </section>
  );
}
