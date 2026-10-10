// Pure text clean-up for OCR output of chat screenshots. No imports, so it can be unit-tested directly.

const TIME_ONLY = /^\d{1,2}:\d{2}\s?(AM|PM|am|pm)?$/;
// read receipts: ✓ ✓✓ ✔ ✅ ☑, which OCR often returns as "vv", "Vv" or "//"
const TICKS_ONLY = /^[\s✓✔✅☑]+$|^[vV/√]{1,3}$/;
const FORWARDED = /^[^\w]*forwarded( many times)?[^\w]*$/i;
// "…t.me/xyz 10:42 AM ✓✓" at the end of a message line. A bare trailing time is kept ("interview at 10:30 AM").
const RECEIPT_TAIL = /\s*\d{1,2}:\d{2}\s?(?:AM|PM|am|pm)?\s*(?:[✓✔✅☑]+|[vV]{1,3}|\/\/)\s*$/;
const TICK_TAIL = /\s*[✓✔✅☑]{1,3}\s*$/;
const LIST_MARKER = /^([-•*·●▪]|\d{1,2}[.)])\s/;
const SENTENCE_END = /[.!?:;]$/;

export function cleanOcrText(raw: string): string {
  const kept: string[] = [];
  for (const rawLine of raw.replace(/\r/g, "").split("\n")) {
    const orig = rawLine.trim();
    const l = orig.replace(RECEIPT_TAIL, "").replace(TICK_TAIL, "").trim();
    if (orig !== "" && l === "") continue; // the line was only a receipt or ticks
    if (l !== "" && (TIME_ONLY.test(l) || TICKS_ONLY.test(l) || FORWARDED.test(l))) continue;
    kept.push(l);
  }

  const out: string[] = [];
  for (const line of kept) {
    if (line === "") {
      if (out.length && out[out.length - 1] !== "") out.push("");
      continue;
    }
    const prev = out[out.length - 1];
    // a wrapped line: the previous one didn't finish a sentence and this one isn't a new list item
    if (prev !== undefined && prev !== "" && !SENTENCE_END.test(prev) && !LIST_MARKER.test(line)) {
      out[out.length - 1] = `${prev} ${line}`;
    } else {
      out.push(line);
    }
  }
  return out.join("\n").replace(/\n{3,}/g, "\n\n").trim();
}
