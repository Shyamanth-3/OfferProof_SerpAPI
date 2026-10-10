import { useEffect, useState, type ReactNode } from "react";
import type { Channel, InterviewFormat, JourneyInput, Sample } from "../api";
import { applyDetected, type Detected } from "../detect";

const inputCls = "w-full rounded-[14px] border border-line bg-raised px-4 py-3 font-sans text-[16px] text-fg placeholder:text-faint";
type Tri = "yes" | "no" | "unsure";
const tri = (v: boolean | null | undefined): Tri => (v === true ? "yes" : v === false ? "no" : "unsure");
const fromTri = (v: Tri): boolean | null => (v === "yes" ? true : v === "no" ? false : null);

const FORMATS: [InterviewFormat, string][] = [
  ["official_portal_or_video", "The company's official portal or video call"],
  ["other_video", "Another video call"],
  ["phone", "Phone call"],
  ["chat_only", "Chat only"],
  ["none", "No interview"],
];
const CHANNELS: [Channel, string][] = [
  ["email", "Email"], ["linkedin", "LinkedIn"], ["job_portal", "Job portal"], ["whatsapp", "WhatsApp"],
  ["telegram", "Telegram"], ["phone_call", "Phone call"], ["other", "Other"],
];

function Panel({ n, title, hint, children }: { n: number; title: string; hint: string; children: ReactNode }) {
  return (
    <details open className="rounded-[14px] border border-line p-4">
      <summary className="cursor-pointer text-[17px] font-medium">
        <span className="meta mr-2 text-faint">{n}</span>
        {title} <span className="meta ml-1 font-normal text-faint">optional</span>
      </summary>
      <p className="meta mt-2 mb-4 text-dim">{hint}</p>
      <div className="flex flex-col gap-3">{children}</div>
    </details>
  );
}

function YesNo({ label, value, onChange }: { label: string; value: Tri; onChange: (v: Tri) => void }) {
  return (
    <fieldset className="m-0 border-0 p-0">
      <legend className="mb-2 p-0 text-[15px]">{label}</legend>
      <div role="radiogroup" aria-label={label} className="flex w-fit rounded-full border border-line p-0.5">
        {(["yes", "no", "unsure"] as Tri[]).map((v) => (
          <button
            key={v}
            type="button"
            role="radio"
            aria-checked={value === v}
            onClick={() => onChange(v)}
            className={`cursor-pointer rounded-full border-0 px-4 py-1.5 text-[13px] ${value === v ? "bg-white text-black" : "bg-transparent text-dim"}`}
          >
            {v === "yes" ? "Yes" : v === "no" ? "No" : "Not sure"}
          </button>
        ))}
      </div>
    </fieldset>
  );
}

const clean = (s: string) => s.trim() || null;

export function JourneyForm({ samples, offerSlot, offerText, detected, setOfferText, busy, modeToggle, modeNote, onSubmit }: {
  samples: [string, Sample][];
  offerSlot: ReactNode; // the same offer box (with screenshot reading) the quick check uses
  offerText: string;
  detected: Detected | null; // company and role found in the pasted offer
  setOfferText: (t: string) => void;
  busy: boolean;
  modeToggle: ReactNode;
  modeNote: string;
  onSubmit: (input: JourneyInput) => void;
}) {
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [autoCompany, setAutoCompany] = useState(false); // value came from the pasted offer, not from the student
  const [autoRole, setAutoRole] = useState(false);
  const [listingUrl, setListingUrl] = useState("");
  const [listingText, setListingText] = useState("");
  const [recName, setRecName] = useState("");
  const [recEmail, setRecEmail] = useState("");
  const [recPhone, setRecPhone] = useState("");
  const [channel, setChannel] = useState<Channel | "">("");
  const [format, setFormat] = useState<InterviewFormat | "">("");
  const [pay, setPay] = useState<Tri>("unsure");
  const [docs, setDocs] = useState<Tri>("unsure");

  // Pre-fill company and role from the pasted offer, never over what the student typed or picked.
  useEffect(() => {
    const out = applyDetected({ company, sender: "", role }, { company: autoCompany, sender: false, role: autoRole }, detected && { ...detected, sender_email: null });
    setCompany(out.fields.company);
    setRole(out.fields.role);
    setAutoCompany(out.auto.company);
    setAutoRole(out.auto.role);
  }, [detected]);

  const build = (): JourneyInput => {
    const listing = { url: clean(listingUrl), text: clean(listingText) };
    const recruiter = { name: clean(recName), email: clean(recEmail), phone: clean(recPhone), channel: channel || null };
    const interview = { format: format || null, asked_to_pay: fromTri(pay), asked_for_documents_before_offer: fromTri(docs) };
    return {
      company: clean(company),
      role: clean(role),
      listing: listing.url || listing.text ? listing : null,
      recruiter: Object.values(recruiter).some(Boolean) ? recruiter : null,
      interview: Object.values(interview).some((v) => v !== null) ? interview : null,
      offer_text: clean(offerText),
    };
  };
  const draft = build();
  const hasStage = Boolean(draft.listing || draft.recruiter || draft.interview || draft.offer_text);

  const fill = (j: JourneyInput) => {
    setAutoCompany(false);
    setAutoRole(false);
    setCompany(j.company ?? "");
    setRole(j.role ?? "");
    setListingUrl(j.listing?.url ?? "");
    setListingText(j.listing?.text ?? "");
    setRecName(j.recruiter?.name ?? "");
    setRecEmail(j.recruiter?.email ?? "");
    setRecPhone(j.recruiter?.phone ?? "");
    setChannel(j.recruiter?.channel ?? "");
    setFormat(j.interview?.format ?? "");
    setPay(tri(j.interview?.asked_to_pay));
    setDocs(tri(j.interview?.asked_for_documents_before_offer));
    setOfferText(j.offer_text ?? "");
  };

  return (
    <form
      className="mt-4 flex flex-col gap-4"
      onSubmit={(e) => {
        e.preventDefault();
        if (hasStage && !busy) onSubmit(draft);
      }}
    >
      <p className="m-0 text-dim">Tell us as much of the journey as you remember. Every part is optional; we judge each stage against how the real company hires.</p>

      <div className="flex flex-wrap gap-2" role="group" aria-label="Sample journeys">
        {samples.map(([k, s]) => (
          <button
            key={k}
            type="button"
            onClick={() => s.journey && fill(s.journey)}
            className="cursor-pointer rounded-full border border-line bg-transparent px-4 py-2 text-[14px] text-fg transition-colors hover:border-white"
          >
            {s.label}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <input id="journey-company" aria-label="Company" value={company} onChange={(e) => { setCompany(e.target.value); setAutoCompany(false); }} placeholder="Company (we can usually find it)" className={`${inputCls} ${autoCompany ? "border-blue/60" : ""}`} />
        <input aria-label="Role" value={role} onChange={(e) => { setRole(e.target.value); setAutoRole(false); }} placeholder="Role (we can usually find it)" className={`${inputCls} ${autoRole ? "border-blue/60" : ""}`} />
      </div>
      {(autoCompany || autoRole) && (
        <p role="status" className="meta m-0 -mt-2 text-blue">
          Detected from your offer: {autoCompany && autoRole ? "company and role" : autoCompany ? "company" : "role"}. Edit if wrong.
        </p>
      )}

      <Panel n={1} title="Where you found the job" hint="A link and/or the listing text. We never open the link: only its web address is looked at.">
        <input aria-label="Listing link" value={listingUrl} onChange={(e) => setListingUrl(e.target.value)} placeholder="Link to the listing" className={inputCls} />
        <textarea aria-label="Listing text" value={listingText} maxLength={10_000} onChange={(e) => setListingText(e.target.value)} placeholder="Paste the listing text" className={`${inputCls} min-h-[110px] resize-y`} />
      </Panel>

      <Panel n={2} title="Who contacted you" hint="Their email and phone are checked just like an offer's sender.">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <input aria-label="Recruiter name" value={recName} onChange={(e) => setRecName(e.target.value)} placeholder="Name" className={inputCls} />
          <input aria-label="Recruiter email" type="email" value={recEmail} onChange={(e) => setRecEmail(e.target.value)} placeholder="Email" className={inputCls} />
          <input aria-label="Recruiter phone" value={recPhone} onChange={(e) => setRecPhone(e.target.value)} placeholder="Phone" className={inputCls} />
          <select aria-label="How they contacted you" value={channel} onChange={(e) => setChannel(e.target.value as Channel | "")} className={inputCls}>
            <option value="">How did they contact you?</option>
            {CHANNELS.map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
      </Panel>

      <Panel n={3} title="The interview" hint="Genuine hiring includes a real interview and never asks for money.">
        <fieldset className="m-0 border-0 p-0">
          <legend className="mb-2 p-0 text-[15px]">How was the interview held?</legend>
          <div role="radiogroup" aria-label="Interview format" className="flex flex-col gap-2">
            {FORMATS.map(([v, l]) => (
              <label key={v} className="flex cursor-pointer items-center gap-3 text-[15px]">
                <input type="radio" name="interview-format" checked={format === v} onChange={() => setFormat(v)} className="h-4 w-4 accent-white" />
                {l}
              </label>
            ))}
          </div>
        </fieldset>
        <YesNo label="Did they ask you to pay?" value={pay} onChange={setPay} />
        <YesNo label="Did they ask for Aadhaar, PAN or bank details before the offer?" value={docs} onChange={setDocs} />
      </Panel>

      <Panel n={4} title="The offer" hint="Paste the offer, or add a screenshot of it.">
        {offerSlot}
      </Panel>

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="submit"
          disabled={!hasStage || busy}
          className="cursor-pointer rounded-full border-0 bg-white px-7 py-3 text-[16px] font-medium text-black disabled:cursor-not-allowed disabled:opacity-40"
        >
          Investigate journey
        </button>
        {modeToggle}
        <span className="meta text-dim">{modeNote}</span>
      </div>
      <p className="meta m-0 text-faint">Aadhaar and PAN numbers are removed before anything is searched.</p>
    </form>
  );
}
