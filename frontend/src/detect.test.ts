// Run with: npm test
import assert from "node:assert/strict";
import { test } from "node:test";
import { applyDetected, describeAuto, NO_AUTO, type Detected } from "./detect.ts";

const empty = { company: "", sender: "", role: "" };
const found: Detected = { company: "Infosys Limited", sender_email: "campus@infosys.com", role: "Systems Engineer" };

test("fills empty fields from the detection and marks them as auto", () => {
  const r = applyDetected(empty, NO_AUTO, found);
  assert.deepEqual(r.fields, { company: "Infosys Limited", sender: "campus@infosys.com", role: "Systems Engineer" });
  assert.deepEqual(r.auto, { company: true, sender: true, role: true });
});

test("never overwrites what the student typed", () => {
  const typed = { company: "My Typed Co", sender: "", role: "" };
  const r = applyDetected(typed, NO_AUTO, found);
  assert.equal(r.fields.company, "My Typed Co");
  assert.equal(r.auto.company, false);
  assert.equal(r.fields.sender, "campus@infosys.com"); // the empty ones still fill
});

test("replaces a previous auto-fill when the text changes", () => {
  const first = applyDetected(empty, NO_AUTO, found);
  const second = applyDetected(first.fields, first.auto, { company: "Wipro", sender_email: null, role: null });
  assert.deepEqual(second.fields, { company: "Wipro", sender: "", role: "" }); // sender and role are no longer found, so cleared
  assert.deepEqual(second.auto, { company: true, sender: false, role: false });
});

test("clears auto-filled fields when there is no detection, but keeps typed ones", () => {
  const first = applyDetected({ ...empty, role: "My role" }, NO_AUTO, found);
  const cleared = applyDetected(first.fields, first.auto, null);
  assert.deepEqual(cleared.fields, { company: "", sender: "", role: "My role" });
  assert.deepEqual(cleared.auto, NO_AUTO);
});

test("a student's edit of an auto-filled field makes it theirs", () => {
  const first = applyDetected(empty, NO_AUTO, found);
  const edited = { fields: { ...first.fields, company: "Infosys BPM" }, auto: { ...first.auto, company: false } }; // what the input handler does
  const later = applyDetected(edited.fields, edited.auto, { company: "Something Else", sender_email: null, role: null });
  assert.equal(later.fields.company, "Infosys BPM");
});

test("describes which fields were filled", () => {
  assert.equal(describeAuto({ company: true, sender: true, role: true }), "company, sender email and role");
  assert.equal(describeAuto({ company: true, sender: false, role: true }), "company and role");
  assert.equal(describeAuto({ company: false, sender: true, role: false }), "sender email");
  assert.equal(describeAuto(NO_AUTO), "");
});
