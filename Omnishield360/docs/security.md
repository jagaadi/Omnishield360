# Security and Governance Notes

## Data handling
- Mask PHI before any external processing step.
- Keep secrets in environment variables or a vault service.
- Avoid hardcoding tenant credentials or API keys.

## Auditability
- Every major decision should emit an audit event.
- Store logs and routing outcomes for review.

## Access control
- Restrict access to queues, folders, and process assets.
- Separate development, QA, and production environments.

## Error handling
- Use retries for transient failures.
- Route exceptions to a review or retry queue where appropriate.

## 2026 governance controls
- PHI tokens are restored from positions computed after all masking passes,
  preventing token replacement collisions.
- Invalid claim contracts halt at Stage 0 with a structured validation code.
- Deceased-member restrictions are claim-scoped. The global outbound halt has
  an expiry marker so unrelated claims are not frozen indefinitely.
- Every execution stage emits an OpenTelemetry span and a structured UiPath log
  fallback with a shared trace ID.
- The Agent-as-Judge checks approval, risk, HITL, routing, and evidence fields
  for contradictions before an approved claim is synchronized.
- Medicare COB decisions use explicit CMS Medicare Secondary Payer context
  (age, current-employment coverage, disability entitlement, and employer
  size). Missing production facts must route to review rather than be inferred.
