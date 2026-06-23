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
