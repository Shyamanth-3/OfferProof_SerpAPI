"""The registered checks, in run order, and the total weight coverage is measured against."""
from .checks import (company_fraud_notice, identifier_trace, impersonation_context, job_listing, registration,
                     sender_identity, template_trace, text_red_flags)

STAGE1 = [sender_identity, impersonation_context, job_listing, registration, text_red_flags]
STAGE2 = [company_fraud_notice, identifier_trace, template_trace]  # need the official domain from stage 1
ORDER = [sender_identity, identifier_trace, template_trace, company_fraud_notice, impersonation_context,
         job_listing, registration, text_red_flags]
TOTAL_WEIGHT = sum(m.WEIGHT for m in ORDER)
assert {m.ID for m in ORDER} == {m.ID for m in STAGE1 + STAGE2}
