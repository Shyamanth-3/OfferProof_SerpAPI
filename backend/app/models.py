from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional

from pydantic import BaseModel, Field, model_validator

Status = Literal["pass", "warn", "fail", "info", "unknown"]
Verdict = Literal["HIGH_RISK", "CAUTION", "NO_RED_FLAGS", "NOT_ENOUGH_EVIDENCE"]


class CheckRequest(BaseModel):
    offer_text: str = Field(min_length=10, max_length=10_000)
    company: Optional[str] = None
    sender_email: Optional[str] = None
    role: Optional[str] = None


class Evidence(BaseModel):
    title: str
    url: str
    snippet: str = ""
    retrieved_at: str
    from_cache: bool = False
    kind: Optional[str] = None  # template_trace: scam_report | reused | official


class CheckResult(BaseModel):
    id: str
    title: str
    status: Status
    weight: int
    scored: bool = False
    finding: str
    engine: Optional[str] = None
    query: Optional[str] = None
    evidence: list[Evidence] = []
    flags: list[str] = []
    phrases: list[str] = []  # template_trace: the exact phrases that were searched
    # internal facts for policy (official_domain, lookalike, ...); not sent to clients
    meta: dict = Field(default_factory=dict, exclude=True)

    @model_validator(mode="after")
    def _scored(self):
        self.scored = self.weight > 0 and self.status in ("pass", "warn", "fail")
        return self


class Identifiers(BaseModel):
    upi: list[str] = []
    phones: list[str] = []
    telegram: list[str] = []
    emails: list[str] = []
    links: list[str] = []


class Extracted(BaseModel):
    company: Optional[str] = None
    sender_email: Optional[str] = None
    role: Optional[str] = None
    identifiers: Identifiers = Identifiers()
    fingerprint: list[str] = []  # phrases template_trace will search (shown so the user sees what was read)


class Override(BaseModel):
    rule: str
    reason: str
    verdict: Verdict


class VerifyKit(BaseModel):
    official_domain: Optional[str] = None
    trusted: bool = False
    careers_url: Optional[str] = None
    role_on_official_site: Optional[bool] = None
    message: str
    mailto: Optional[str] = None
    advice: str


class CheckResponse(BaseModel):
    verdict: Verdict
    verdict_label: str
    risk_score: Optional[int]
    coverage: float
    overrides: list[Override]
    extracted: Extracted
    redacted: list[str]
    checks: list[CheckResult]
    next_steps: list[str]
    verify_kit: Optional[VerifyKit] = None
    searches_used: int
    elapsed_ms: int
    mode: str


@dataclass
class Ctx:
    """Shared, read-mostly input for every check."""

    text: str
    company: Optional[str]
    role: Optional[str]
    sender_email: Optional[str]
    identifiers: Identifiers
    official: list[str] = field(default_factory=list)  # filled after sender_identity
    trusted: list[str] = field(default_factory=list)  # subset of official: knowledge panel or known-company list
    sender_on_official: bool = False
    extracted: Optional[Extracted] = None
    journey: Optional[JourneyInput] = None  # set only by /api/investigate

    @property
    def official_domain(self) -> Optional[str]:
        """Best domain to talk about: a trusted one if we have it, else the top guess, else None."""
        return (self.trusted or self.official or [None])[0]

    @property
    def official_domain_trusted(self) -> bool:
        return bool(self.trusted)


# ---- investigate the full journey -------------------------------------------------------------
Channel = Literal["email", "linkedin", "job_portal", "whatsapp", "telegram", "phone_call", "other"]
InterviewFormat = Literal["official_portal_or_video", "other_video", "phone", "chat_only", "none"]
MAX_FIELD = 10_000  # same per-field limit as /api/check


def _blank_to_none(v):
    return v.strip() or None if isinstance(v, str) else v


class ListingStage(BaseModel):
    url: Optional[str] = Field(None, max_length=MAX_FIELD)  # where the student saw the job. NEVER fetched.
    text: Optional[str] = Field(None, max_length=MAX_FIELD)  # pasted listing text

    def has_content(self) -> bool:
        return bool(_blank_to_none(self.url) or _blank_to_none(self.text))


class RecruiterStage(BaseModel):
    name: Optional[str] = Field(None, max_length=MAX_FIELD)
    email: Optional[str] = Field(None, max_length=MAX_FIELD)
    phone: Optional[str] = Field(None, max_length=MAX_FIELD)
    channel: Optional[Channel] = None

    def has_content(self) -> bool:
        return bool(_blank_to_none(self.name) or _blank_to_none(self.email) or _blank_to_none(self.phone) or self.channel)


class InterviewStage(BaseModel):
    format: Optional[InterviewFormat] = None
    asked_to_pay: Optional[bool] = None
    asked_for_documents_before_offer: Optional[bool] = None  # Aadhaar/PAN/bank details before any offer

    def has_content(self) -> bool:
        return any(v is not None for v in (self.format, self.asked_to_pay, self.asked_for_documents_before_offer))


class JourneyInput(BaseModel):
    company: Optional[str] = Field(None, max_length=MAX_FIELD)
    role: Optional[str] = Field(None, max_length=MAX_FIELD)
    listing: Optional[ListingStage] = None
    recruiter: Optional[RecruiterStage] = None
    interview: Optional[InterviewStage] = None
    offer_text: Optional[str] = Field(None, max_length=MAX_FIELD)

    @model_validator(mode="after")
    def _at_least_one_stage(self):
        stages = [self.listing and self.listing.has_content(), self.recruiter and self.recruiter.has_content(),
                  self.interview and self.interview.has_content(), _blank_to_none(self.offer_text)]
        if not any(stages):
            raise ValueError("Give details for at least one stage: listing, recruiter, interview or offer.")
        return self


class TimelineNode(BaseModel):
    stage: Literal["listing", "recruiter", "interview", "payment", "offer"]
    status: Literal["matches", "diverges", "unverified", "not_provided"]
    headline: str
    check_ids: list[str] = []


class Divergence(BaseModel):
    stage: str
    reason: str


class JourneyResponse(CheckResponse):
    timeline: list[TimelineNode]
    first_divergence: Optional[Divergence] = None
