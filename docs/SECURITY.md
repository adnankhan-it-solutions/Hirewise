# Security

## Enforced application controls

Argon2 password hashing; >=12-character passwords with common-password and similarity validation; CSRF on browser mutations; HttpOnly/SameSite sessions; HTTPS/Secure cookies/HSTS outside development; CSP; no framing; private no-store/noindex responses; mandatory admin TOTP with encrypted secret and replay counter; server-side role, verification and tenant gates; single-use hashed email/guest tokens; session-bound document links expiring in 120 seconds; download-time authorization and file hash checking; logged human decisions; configurable blind review; parameterized ORM queries and escaped templates.

Throttles use shared database counters for login, MFA, registration, applications, recovery, rescreening and invitations. Deploy an edge request/body-size limiter and monitoring in addition. Application throttles do not replace credential-stuffing detection. User-controlled forwarded IPs are not trusted. Only enable TRUST_PROXY where the proxy strips inbound forwarding headers.

Uploads require matching extension, MIME and file signature; DOCX archive size/count limits; no active macros; UTF-8 text validation; 5 MB maximum. Quarantine is private. `clamdscan` must succeed before extraction or download. Parser subprocess receives only document bytes, extension and a minimal environment, with CPU/memory/time limits. Run the worker as an unprivileged isolated service with outbound network denied except private storage/DB/scanner. No candidate-provided URL is fetched.

## Remaining production verification

Review THREAT_MODEL.md and LAUNCH_CHECKLIST.md. Configure tested scanner/signature updates, immutable external audit retention, MFA recovery procedure, SMTP/domain reputation, encrypted storage/DB/backup, private networking, dependency scanning and external penetration testing. A clean dependency audit is not a security certification. Application audit has no UI/API edit/delete operations, but DB operators can modify records until separate DB permissions and immutable archival controls are deployed.

The public repository must never contain credentials, `.env`, applicant documents, database files or real test data. The generated SSH private key is outside this repository. Report security issues privately to the configured support contact; do not post candidate records or secrets in public issues.
