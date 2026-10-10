"""The registered checks, in run order, and the total weight coverage is measured against."""
from .checks import (company_fraud_notice, identifier_trace, impersonation_context, job_listing, registration,
                     official_careers, sender_identity, template_trace, text_red_flags, listing_source, listing_clone,
                     recruiter_trace, interview_process, listing_offer_consistency)

STAGE1 = [sender_identity, impersonation_context, job_listing, registration, text_red_flags]
STAGE2 = [company_fraud_notice, identifier_trace, template_trace, official_careers]  # need the official domain from stage 1
ORDER = [sender_identity, identifier_trace, template_trace, company_fraud_notice, official_careers, impersonation_context,
         job_listing, registration, text_red_flags]
TOTAL_WEIGHT = sum(m.WEIGHT for m in ORDER)
assert {m.ID for m in ORDER} == {m.ID for m in STAGE1 + STAGE2}

# /api/investigate runs everything above plus the journey checks. Quick check keeps using ORDER/TOTAL_WEIGHT.
JOURNEY_STAGE1 = STAGE1 + [recruiter_trace, listing_offer_consistency]
JOURNEY_STAGE2 = STAGE2 + [listing_source, listing_clone, interview_process]
JOURNEY_ORDER = [listing_source, listing_clone, sender_identity, identifier_trace, recruiter_trace, interview_process,
                 template_trace, listing_offer_consistency, company_fraud_notice, official_careers, impersonation_context,
                 job_listing, registration, text_red_flags]
JOURNEY_TOTAL_WEIGHT = sum(m.WEIGHT for m in JOURNEY_ORDER)
assert {m.ID for m in JOURNEY_ORDER} == {m.ID for m in JOURNEY_STAGE1 + JOURNEY_STAGE2}
