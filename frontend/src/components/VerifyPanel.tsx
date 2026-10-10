import { useState } from "react";
import type { VerifyKit } from "../api";

const btn = "cursor-pointer rounded-full px-5 py-2.5 text-[15px] font-medium no-underline";

export function VerifyPanel({ kit }: { kit: VerifyKit }) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(kit.message);
    } catch {
      // clipboard blocked (e.g. insecure context): fall back to a temporary textarea
      const t = document.createElement("textarea");
      t.value = kit.message;
      document.body.appendChild(t);
      t.select();
      document.execCommand("copy");
      t.remove();
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section aria-labelledby="verify-title" className="fade-up rounded-[14px] border border-line p-6" style={{ animationDelay: "440ms" }}>
      <div className="flex flex-wrap items-center gap-3">
        <h2 id="verify-title" className="m-0 text-[27px] font-medium">
          Verify it yourself
        </h2>
        {kit.role_on_official_site === true && (
          <span className="meta rounded-full border border-green/50 px-3 py-1 text-green">Role listed on official site ✓</span>
        )}
      </div>
      <p className="mt-3 mb-0 text-dim">{kit.advice}</p>

      <div className="mt-5 flex flex-wrap gap-3">
        {kit.careers_url && (
          <a href={kit.careers_url} target="_blank" rel="noopener noreferrer" className={`${btn} bg-white text-black`}>
            Open official careers page
          </a>
        )}
        <button type="button" onClick={copy} className={`${btn} border border-white bg-transparent text-fg`}>
          {copied ? "Copied ✓" : "Copy message"}
        </button>
        {kit.mailto && (
          <a href={kit.mailto} className={`${btn} border border-line text-fg`}>
            Email the company
          </a>
        )}
      </div>
      <span className="sr-only" role="status">
        {copied ? "Message copied to clipboard" : ""}
      </span>

      <p className="meta mt-6 mb-2 text-faint">Message to send (find the company's address on its official site):</p>
      <pre
        tabIndex={0}
        aria-label="Message to send to the company"
        className="m-0 rounded-[8px] bg-[#0c0c0c] p-4 font-mono text-[13px] leading-relaxed whitespace-pre-wrap text-dim select-all"
      >
        {kit.message}
      </pre>
    </section>
  );
}
