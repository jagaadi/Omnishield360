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
