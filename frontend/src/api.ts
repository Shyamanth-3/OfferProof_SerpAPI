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

export interface Sample {
  label: string;
  offer_text: string;
  company?: string;
  sender_email?: string;
  role?: string;
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
