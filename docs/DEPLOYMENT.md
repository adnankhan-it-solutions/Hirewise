# Deployment

## GitHub project website (owner-requested immediate target)

The repository has `.github/workflows/pages.yml`. It deploys only the data-free static project site, after Application checks succeeds. In repository **Settings → Pages → Build and deployment → Source**, select **GitHub Actions**. No custom domain purchase is needed. Expected URL after a successful deployment:

https://adnankhan-it-solutions.github.io/Hirewise/

This is an expected address, not evidence of a completed deployment. Verify the Actions deployment and load the URL before announcing it live. Repository write authentication and permission to configure Pages are required. An SSH deploy key grants Git write but does not grant REST API access to Pages settings.

Local build: `python manage.py build_public_site --base-path /Hirewise/`. Output `public-site/` is ignored. Only explicit public routes are rendered; no DB export. GitHub Pages is static hosting and cannot run Django, PostgreSQL, background jobs, private uploads or payments. See https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages . GitHub Pages is used here as a project introduction; review GitHub's current usage rules before any commercial-site expansion.

## Authenticated application (not deployed)

1. Obtain owner approval for infrastructure charges and counsel approval for regions/providers.
2. Provision separate staging and production PostgreSQL, private encrypted S3-compatible buckets, SMTP provider, scanner/worker and web services. Do not expose DB or scanner publicly.
3. Configure environment from `.env.example`. Generate a long random SECRET_KEY and independent Fernet MFA_ENCRYPTION_KEY in the secret manager. Set ENVIRONMENT=production, HTTPS PUBLIC_ORIGIN, explicit ALLOWED_HOSTS, CSRF_TRUSTED_ORIGINS, SMTP and storage. Use a PostgreSQL URL requiring TLS.
4. Build `docker build -f deploy/Dockerfile -t hirewise:<commit> .`. Container runs as an unprivileged user. Runtime user must have only necessary database privileges; migration/audit roles are separate.
5. Back up DB, run `python manage.py migrate` with the migration role, collect static at image build, start web service on port 8000 behind managed HTTPS. Configure trusted proxy only with header stripping.
6. Install/configure clamdscan in an isolated worker image, keep signatures updated, run `process_documents` and `deliver_notifications` every minute. Monitor retries and stuck leases. Worker/scanner image hardening is an outstanding production task.
7. Run `python manage.py create_admin <owner-email>` interactively over authorized secure administration, then enroll MFA. Never deploy demo passwords/data.
8. Run production `check --deploy`, all tests against PostgreSQL, real malware test fixtures, staging mail/retention/recovery drills and external security review.
9. Complete LAUNCH_CHECKLIST.md. Production application intake is disabled by default and cannot be toggled by the generic settings form. Enable only through an audited deployment after every gate is signed off.

No live payment configuration is included. Internal test receipts are not tax invoices, sandbox entitlements cannot unlock paid jobs. Rollback requires a compatible application image; migrations are not blindly reversed. Follow BACKUP_RECOVERY.md for data recovery.

Render preview free tiers sleep and expire databases; never place real candidate data there without paid backup/storage and reviewed availability. See BLUEPRINT.md for current sources, costs and upgrade triggers.
