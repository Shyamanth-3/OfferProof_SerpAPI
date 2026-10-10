// Types mirror backend/app/models.py exactly.
export type Status = "pass" | "warn" | "fail" | "info" | "unknown";
export type Verdict = "HIGH_RISK" | "CAUTION" | "NO_RED_FLAGS" | "NOT_ENOUGH_EVIDENCE";
export type Mode = "live" | "cached";

export interface CheckRequest {
  offer_text: string;
  company?: string | null;
  sender_email?: string | null;
  role?: string | null;
}

export interface Evidence {
  title: string;
  url: string;
  snippet: string;
  retrieved_at: string;
  from_cache: boolean;
  kind?: "scam_report" | "reused" | "official" | null;
}

export interface CheckResult {
  id: string;
  title: string;
  status: Status;
  weight: number;
  scored: boolean;
  finding: string;
  engine: string | null;
  query: string | null;
  evidence: Evidence[];
  flags: string[];
  phrases: string[];
  skipped?: "slow" | "failed" | "not_recorded" | "capped" | null; // why the check didn't run
}

export interface Identifiers {
  upi: string[];
  phones: string[];
  telegram: string[];
  emails: string[];
  links: string[];
}

export interface Extracted {
  company: string | null;
  sender_email: string | null;
  role: string | null;
  identifiers: Identifiers;
  fingerprint: string[];
}

export interface Override {
  rule: string;
  reason: string;
  verdict: Verdict;
}

export interface VerifyKit {
  official_domain: string | null;
  trusted: boolean;
  careers_url: string | null;
  role_on_official_site: boolean | null;
  message: string;
  mailto: string | null;
  advice: string;
}

export interface CheckResponse {
  verdict: Verdict;
  verdict_label: string;
  risk_score: number | null;
  coverage: number;
  overrides: Override[];
  extracted: Extracted;
  redacted: string[];
  checks: CheckResult[];
  next_steps: string[];
  verify_kit: VerifyKit | null;
  searches_used: number;
  elapsed_ms: number;
  mode: string;
}

export type Channel = "email" | "linkedin" | "job_portal" | "whatsapp" | "telegram" | "phone_call" | "other";
export type InterviewFormat = "official_portal_or_video" | "other_video" | "phone" | "chat_only" | "none";

export interface JourneyInput {
  company?: string | null;
  role?: string | null;
  listing?: { url?: string | null; text?: string | null } | null;
  recruiter?: { name?: string | null; email?: string | null; phone?: string | null; channel?: Channel | null } | null;
  interview?: { format?: InterviewFormat | null; asked_to_pay?: boolean | null; asked_for_documents_before_offer?: boolean | null } | null;
  offer_text?: string | null;
}

export type TimelineStage = "listing" | "recruiter" | "interview" | "payment" | "offer";
export interface TimelineNode {
  stage: TimelineStage;
  status: "matches" | "diverges" | "unverified" | "not_provided";
  headline: string;
  check_ids: string[];
}
export interface JourneyResponse extends CheckResponse {
  timeline: TimelineNode[];
  first_divergence: { stage: string; reason: string } | null;
}

export interface Sample {
  label: string;
  kind?: "quick" | "journey";
  offer_text?: string; // quick samples
  company?: string;
  sender_email?: string;
  role?: string;
  journey?: JourneyInput; // journey samples
}

async function http<T>(url: string, init?: RequestInit): Promise<T> {
  const r = await fetch(url, init);
  if (!r.ok) {
    let detail = "";
    try {
      const j = await r.json();
      detail = typeof j.detail === "string" ? j.detail : "";
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail || `Request failed (${r.status})`);
  }
  return r.json() as Promise<T>;
}

export const getSamples = () => http<Record<string, Sample>>("/api/samples");

export const runCheck = (body: CheckRequest, mode: Mode) =>
  http<CheckResponse>(`/api/check?mode=${mode}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const getQuota = (mode: Mode) =>
  http<{ total_searches_left: number | null }>(`/api/quota?mode=${mode}`);

export const runJourney = (body: JourneyInput, mode: Mode) =>
  http<JourneyResponse>(`/api/investigate?mode=${mode}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

export const detectOffer = (offer_text: string, signal?: AbortSignal) =>
  http<{ company: string | null; sender_email: string | null; role: string | null }>("/api/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ offer_text }),
    signal,
  });
