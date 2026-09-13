# Hirewise startup hosting

This directory packages the complete Django application for a single-server test/staging environment: HTTPS proxy, web app, PostgreSQL, MinIO private object storage, ClamAV, document worker and email/retention workers. It is separate from the static GitHub Pages introduction.

## What this can host

- recruiter/candidate accounts, email verification and administrator MFA;
- company-scoped vacancies and applications;
- private CV quarantine, antivirus scanning and extraction;
- evidence-baseline screening, text interviews and sandbox payments;
- PostgreSQL persistence, MinIO object persistence and local encrypted backup archives.

GitHub stores this configuration and source but does not run these containers. Sharing the full application requires a Linux server/VPS with a public IP and domain. The owner has not supplied one, so no publicly reachable backend has been deployed.

## Start a synthetic-data test stack

Requirements: Docker Engine with Compose v2, at least 4 CPU, 8 GB RAM and 30 GB free disk. ClamAV is resource intensive. From the repository root:

```sh
cp startup_hosting/.env.hosting.example startup_hosting/.env.hosting
```

Generate every `CHANGE_ME` value with a password manager. Generate `MFA_ENCRYPTION_KEY` using:

```sh
docker compose --env-file startup_hosting/.env.hosting -f startup_hosting/compose.yaml run --rm web python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

For a test machine set `SITE_ADDRESS=:8080`, `PUBLIC_ORIGIN=http://localhost:8080`, and keep `ENVIRONMENT=development` and `PRODUCTION_INTAKE_ENABLED=0`. Then:

```sh
docker compose --env-file startup_hosting/.env.hosting -f startup_hosting/compose.yaml up --build -d
docker compose --env-file startup_hosting/.env.hosting -f startup_hosting/compose.yaml run --rm web python manage.py migrate
docker compose --env-file startup_hosting/.env.hosting -f startup_hosting/compose.yaml run --rm web python manage.py seed_demo
```

Open `http://localhost:8080`. Run the full validation script before sharing:

```sh
startup_hosting/verify_stack.sh
```

The demo command prints randomized credentials once. It refuses to run outside development. Do not commit `.env.hosting`, credentials, database volumes, backups or applicant documents.

## Public staging/production

Before using a domain, complete `docs/LAUNCH_CHECKLIST.md`. Set a real `SITE_ADDRESS` domain, HTTPS `PUBLIC_ORIGIN`, SMTP, strong independent secrets, `ENVIRONMENT=production`, explicit hosts/origins, and reviewed storage encryption/backup. Production settings reject SQLite, HTTP, missing SMTP and missing MFA encryption.

The included MinIO stack is for synthetic staging. Its application-level S3 encryption header is disabled because a standalone MinIO server needs KMS configuration for server-side encryption. Real candidate data requires encrypted server disks plus a reviewed KMS-backed object-storage deployment, or a managed encrypted S3-compatible bucket. Do not enable production intake in this compose file merely by changing an environment variable; the application database launch gate must be changed through an audited launch operation after every checklist item is complete.

## Operations

`web` serves HTTP only inside the private compose network. Caddy is the sole published service. PostgreSQL, MinIO and ClamAV expose no host ports. Health checks gate startup. The document worker waits for ClamAV, then runs bounded batches every 15 seconds. Mail outbox runs every 30 seconds. Retention runs preview-only; an authorized operator must execute reviewed retention separately.

Back up with `startup_hosting/backup.sh`; it writes a date-stamped encrypted archive to `startup_hosting/backups/` using `BACKUP_PASSPHRASE`. Copy archives to separate restricted storage. Restore only through the documented recovery drill; the package intentionally has no one-command production overwrite.

Stop without deleting data:

```sh
docker compose --env-file startup_hosting/.env.hosting -f startup_hosting/compose.yaml down
```

Deleting volumes is destructive and is not part of this guide.
