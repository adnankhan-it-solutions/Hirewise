# Hirewise

Recruitment platform for Qatar with private company workspaces, candidate accounts and human-led decisions.

**In development; not approved for real applicant intake.** See [blueprint](docs/BLUEPRINT.md) and [milestone status](docs/MILESTONES.md). No live payment/AI provider or production hosting is configured.

## Run locally

Python 3.12 recommended (3.10+ supported by the selected Django LTS).

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python manage.py migrate
.venv/bin/python manage.py runserver
```

Open http://localhost:8000. SQLite is local-only. Configure `DATABASE_URL` for PostgreSQL. Never use local development settings for production. Environment variables are read from the process; `.env.example` is a reference, not automatically loaded.

The supplied startup logo is used through `static/logo.webp`; the original high-resolution `static/logo.png` is retained. For a shareable full test environment with PostgreSQL, private CV storage, antivirus and workers, follow [startup_hosting/README.md](startup_hosting/README.md). A local folder does not create public hosting: a public Linux server and domain are still required for the authenticated service.

Register through the UI. Run `python manage.py deliver_notifications` for queued email; development uses console delivery. Create an administrator interactively with `python manage.py create_admin owner@example.com`; enroll an authenticator at first login. No default production credentials exist.

```sh
.venv/bin/python manage.py test
.venv/bin/python -m ruff check .
.venv/bin/python manage.py check
.venv/bin/python manage.py makemigrations --check --dry-run
```

After starting the local server, install `requirements-dev.txt` and run `python scripts/browser_smoke.py` for the synthetic candidate CV-upload and recruiter-decision browser workflow.

Source is kept in the `app/` checkout within the shared workspace; this README is at the Git repository root.
