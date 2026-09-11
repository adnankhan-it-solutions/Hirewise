# Operating costs and scale

BLUEPRINT.md section K contains a component-by-component USD planning model for 1,000 / 10,000 / 100,000 applications monthly. Estimated totals excluding payment fees/taxes/domain/labor/legal/testing are $88–173 / $415–705 / $3,170–4,870. Assumptions: 2 MB/CV, six-month retained originals plus one backup, four emails/application, 20% text interviews, AI budget assumption $0.015/application + $0.04/interview. This is a planning allowance, not a provider quote or measured workload result. Actual current external AI/transcription usage is zero because providers are not configured.

Expected steady-state retained storage plus backup is approximately 24/240/2,400 GB. Payment fees require merchant quotes and transaction counts; applicant count does not determine payment cost. Free public GitHub Pages has platform limits and contains only public project content; it is not free backend/database/document hosting.

Scale path: index/paginate tenant queries first; monitor p95 latency and DB query plans; run document/email work off web requests; increase worker capacity when queue age exceeds five minutes; connection pooling and PostgreSQL capacity before increasing web replicas; keep documents in shared storage; add semantic provider/caching only with measured value and approved privacy controls. Avoid keeping sessions/files on local instance disks.

Upgrade triggers: sustained database/CPU >70%, storage >70% allocation, p95 ordinary response >750 ms, queue age >5 minutes, provider rate-limit pressure or recovery targets unmet. These are starting operational thresholds to validate in load tests. No production load test has established that the current code supports 100,000 monthly applications.
