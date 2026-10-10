// Run with: npm test   (Node's built-in test runner; Node 22 runs TypeScript directly)
import assert from "node:assert/strict";
import { test } from "node:test";
import { cleanOcrText } from "./ocrClean.ts";

test("drops timestamp-only lines but keeps lines that merely contain a time", () => {
  const out = cleanOcrText("Hello there\n10:42 AM\n9:05\nInterview at 10:30 AM tomorrow.\n11:59 pm");
  assert.equal(out, "Hello there Interview at 10:30 AM tomorrow.");
});

test("drops read-receipt ticks and OCR misreads of them", () => {
  assert.equal(cleanOcrText("Pay now.\n✓✓\n✓\nvv\nThanks."), "Pay now.\nThanks.");
});

test("drops a receipt whose ticks OCR read as letters", () => {
  assert.equal(cleanOcrText("Join now.\n10:42 AM vv\nThanks."), "Join now.\nThanks.");
  assert.equal(cleanOcrText("Join t.me/x 10:42 AM //"), "Join t.me/x");
  assert.equal(cleanOcrText("Interview at 10:30 AM"), "Interview at 10:30 AM"); // a bare time is content
});

test("drops Forwarded labels", () => {
  assert.equal(cleanOcrText("Forwarded\nForwarded many times\nYou are selected."), "You are selected.");
  assert.equal(cleanOcrText("↪ Forwarded\nJoin now."), "Join now.");
});

test("merges lines broken mid-sentence", () => {
  const out = cleanOcrText("You are selected for the Work From\nHome Data Entry Internship at a\ntop company.");
  assert.equal(out, "You are selected for the Work From Home Data Entry Internship at a top company.");
});

test("keeps paragraphs, list items and sentence ends", () => {
  const out = cleanOcrText("Dear Student,\n\nBenefits:\n- Job guarantee\n- Stipend\n\nEnroll now.");
  assert.equal(out, "Dear Student,\n\nBenefits:\n- Job guarantee\n- Stipend\n\nEnroll now.");
});

test("collapses blank-line runs and handles empty input", () => {
  assert.equal(cleanOcrText("A.\n\n\n\n\nB."), "A.\n\nB.");
  assert.equal(cleanOcrText(""), "");
  assert.equal(cleanOcrText("10:42 AM\n✓✓"), "");
});

test("a realistic chat screenshot", () => {
  const raw = "Forwarded\nCongratulations! You are selected for\nWork From Home internship.\nPay Rs. 1,999 refundable fee to\nabc@okaxis and join t.me/xyz\n10:42 AM ✓✓\n10:43 AM\n✓✓";
  const out = cleanOcrText(raw);
  assert.match(out, /^Congratulations! You are selected for Work From Home internship\./m);
  assert.match(out, /Pay Rs\. 1,999 refundable fee to abc@okaxis and join t\.me\/xyz/);
  assert.doesNotMatch(out, /Forwarded|AM/);
});
