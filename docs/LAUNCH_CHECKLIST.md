# Launch checklist

## Public GitHub project site

- [x] Public, data-free static export and no intake/account forms.
- [x] Responsive desktop/mobile design and local browser check.
- [x] Static links use the repository base path.
- [x] GitHub Actions test/build and Pages workflow supplied.
- [x] Push commit and inspect actual GitHub Actions result: application checks passed on PostgreSQL 16 and container build.
- [x] Owner set repository Pages source to GitHub Actions.
- [ ] Verify the live URL and pages/CSS/HTTPS after deployment.

## Authenticated production service — intake remains disabled

- [ ] Approved business identity, support contact and domain.
- [ ] Owner approval for paid infrastructure and merchant/AI enrollment.
- [ ] Qatar legal/commercial/privacy/fairness/transfer review (LEGAL_REVIEW.md).
- [ ] Managed PostgreSQL private networking/TLS and runtime/migration/audit roles.
- [ ] Private encrypted object store, versioned-object deletion and backup policy.
- [ ] Scanner service with fresh signatures, malicious/clean fixtures and fail-safe tests.
- [ ] Hardened worker image/network policy, monitored queue/retries and outbox.
- [ ] Production secrets, administrator MFA recovery and session-revocation operations.
- [ ] Verified email provider/domain, real delivery, reset/recovery and reminders.
- [ ] Complete schema-validated semantic/contextual matching provider and fairness validation.
- [ ] Complete AI interview generation/assessment provider with evidence validation, or explicitly launch a reviewed non-AI scope.
- [ ] Live Qatar merchant onboarding, documented adapter, sandbox certification, refunds/reconciliation.
- [ ] Accountant-approved invoice/tax fields and legal entity details.
- [ ] Complete candidate account deletion and legal hold/admin workflows.
- [ ] Complete requested owner administration and analytics capabilities.
- [ ] External penetration-oriented review; negative tests on deployed PostgreSQL and storage.
- [ ] Automated encrypted backups and successful documented restore drill.
- [ ] Monitoring, incident contacts, error/queue alerts, uptime and rollback drill.
- [ ] Separate staging/production secrets and no default/demo passwords/data.
- [ ] Production configuration check and deploy-time authorization to enable intake.

## Startup hosting package verification

- [x] Compose file parsed successfully; PostgreSQL, object storage and ClamAV publish no host ports.
- [x] Shell scripts passed syntax checks.
- [x] Local real-browser workflow passed: candidate login, CV upload/confirmation, recruiter blind review and reasoned shortlist.
- [ ] Build and run the container stack on a Docker-capable machine (Docker is unavailable in this development environment).
- [ ] Verify real ClamAV clean/malware handling and MinIO persistence through container restarts.
- [ ] Supply a public server/domain and complete every production gate before real data intake.

Unmarked items are genuinely outstanding. Do not announce the complete commercial recruitment service as ready based on static-site deployment or passing local unit tests.
