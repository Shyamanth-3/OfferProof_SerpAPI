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

    @property
    def official_domain(self) -> Optional[str]:
        """Best domain to talk about: a trusted one if we have it, else the top guess, else None."""
        return (self.trusted or self.official or [None])[0]

    @property
    def official_domain_trusted(self) -> bool:
        return bool(self.trusted)
