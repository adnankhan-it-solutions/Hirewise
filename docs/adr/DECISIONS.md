# Architecture decision records

## ADR-001 — Authentication

Options: managed identity or Django sessions. Decision: Django custom UUID user, database sessions, Argon2 and mandatory admin TOTP. Reason: mature integrated CSRF/forms, no external account dependency or per-user fees. Security: MFA secret encryption and server gates; recovery/step-up still required. Migration: map stable user UUIDs to a future managed IdP/SSO.

## ADR-002 — Database

Options: PostgreSQL, MySQL, SQLite. Decision: PostgreSQL production, SQLite local convenience only. Reason: transactions, constraints, JSON and indexes; relational applicant/audit model. Cost: managed DB is paid for safe production backups. Security: query scoping now, runtime roles and possible RLS later. Migration: native Django migrations; avoid SQLite-specific SQL.

## ADR-003 — Documents

Options: public uploads, instance disk, private object storage. Decision: private S3-compatible quarantine with explicit authorization; local private storage development only. Security: signatures/limits, antivirus, isolated extraction, session-bound 120-second downloads and hash verification. Cost: capacity/request/backup charges. Migration: storage-key abstraction and standard S3 adapter.

## ADR-004 — AI provider

Options: hosted AI, local model, deterministic baseline. Decision: explicit baseline only until owner-approved provider/privacy contract. Reason: no provider credentials or consented production infrastructure exists; never fabricate semantic intelligence. Security: no candidate AI disclosure now. Cost: zero external AI now, estimated future allowance separately. Migration: provider protocols, versioned evidence records; full structured integration is outstanding.

## ADR-005 — Payments

Options: assume global gateway, implement invented Qatar API, wait for actual merchant specs. Decision: internal sandbox adapter now; QNB/acquirer-compatible live adapter only from official merchant specs. Security: test HMAC/amount/replay checks, no live entitlements from test payments. Cost: no transaction fees now; negotiate later. Migration: PaymentProviderInterface.

## ADR-006 — Hosting

Options: full cloud backend, GitHub Pages, local development. Owner requests GitHub hosting and has no cloud account. Decision: GitHub Pages public project site plus full application source/container configuration. GitHub Pages cannot host private backend workflows. Security: static allowlist exports no candidate data. Cost: public project hosting subject to GitHub limits; real backend incurs costs. Migration: deploy Django separately and route public calls to the reviewed application host.

## ADR-007 — Matching

Options: opaque score, evidence-bearing baseline, full hybrid model. Decision: conservative baseline with per-criterion source excerpts, unknowns and immutable run snapshots. Every baseline recommendation requires human review. Security: no tools/actions from documents; injection-like text withholds score. Cost: local processing. Migration: add schema-validated normalized facts, embeddings and contextual provider with evidence/fairness tests.

## ADR-008 — Retention

Options: indefinite retention, fixed hardcoded purge, jurisdiction-configured policy. Decision: configurable default with per-application expiry, legal hold, preview/explicit execute batch. Default 180 days is provisional, not legal advice. Security: originals/derived content scrubbed; immutable minimal tombstone. Cost: bounds storage; backup deletion reconciliation outstanding. Migration: add country-specific policy/version models after counsel approval.
