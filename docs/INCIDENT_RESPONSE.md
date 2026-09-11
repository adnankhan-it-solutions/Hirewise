# Incident response and continuity

Assign an incident lead, technical responder, privacy/legal contact and communications owner before launch. Public support email must be configured. No automated external incident communications are sent by this repository.

1. Triage: record UTC time, affected systems, correlation IDs, indicators and scope without copying CVs unnecessarily. Preserve restricted evidence and immutable logs.
2. Contain: revoke affected sessions/credentials, suspend compromised company/user access, isolate exposed storage/worker, stop provider calls or payment activation if integrity is uncertain. Preserve applications and transaction history.
3. Assess: investigate tenant scope, exposed categories, actors, duration and actual access. Counsel determines notification duties/deadlines; do not invent them.
4. Eradicate: patch root cause, rotate secrets, rebuild trusted images and remove unauthorized grants. Verify with regression/negative tests and dependency scans.
5. Recover: restore only from verified backups if required, replay deletion records, reconcile payments with the provider, confirm private storage/tenant access and monitor elevated risk.
6. Review: record decisions, approved communications, corrective actions, owners and follow-up dates.

AI outage: preserve applications, show processing unavailable, retry bounded tasks; public browsing stays available. Email outage: outbox retries with backoff and alerts after exhausted attempts. Payment outage: leave pending/unpaid, reconcile server-side; never grant entitlement on a success redirect. Database outage: readiness returns 503, writes stop safely; follow backup runbook. Storage/scanner outage: uploads fail safely or stay quarantined; no unscanned download. Deployment regression: route to prior compatible image and inspect migration compatibility before rollback.
