# Operations Runbook

## Normal operation
1. Monitor Orchestrator jobs and queue items.
2. Review logs for status transitions and human review routing.
3. Verify audit events for completed or halted cases.

## Exception handling
- If an OCR threshold is missed, route to validation.
- If a referral is missing, notify the provider workflow.
- If a duplicate or compliance issue is detected, pause the run and route to the correct review queue.

## Recovery steps
- Re-run failed queue items after correcting the source data.
- Confirm any downstream system sync success before closing the case.
- Recheck secrets and environment values if authentication fails.

## Circuit-breaker recovery
1. Confirm the claim-specific breaker asset before touching the global flag.
2. Review the Legal Estates Action Center task and evidence binder reference.
3. Do not clear the claim-specific asset without Legal approval.
4. Treat the global expiry asset as a re-evaluation time, not automatic
   permission to bill the affected claim.

## Judge-review recovery
1. Open the `SUSPENDED_JUDGE_REVIEW` case in Action Center.
2. Compare the deterministic conflict codes with the stage evidence.
3. Correct the upstream data or decision; do not manually overwrite the final
   risk tier without recording the reason.

## Medicare COB review
1. Confirm whether group coverage is based on current employment.
2. Confirm beneficiary age, disability entitlement, and employer size.
3. Verify payer types (`MEDICARE`, `EMPLOYER_GHP`, and
   `MEDICARE_SUPPLEMENT`) before accepting the automated order.
4. Escalate ESRD, workers' compensation, liability/no-fault, VA, or other
   unmodeled payer situations to a COB specialist.
