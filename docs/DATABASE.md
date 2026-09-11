# Database

Production target: PostgreSQL; local/unit tests may use SQLite. Migrations `0001` accounts/company/audit, `0002` vacancies/applications/documents/scoring, `0003` interviews/billing/team. UUID primary keys for exposed domain records. Email is unique case-insensitively for users. Verified applications have a conditional unique job/email constraint. Membership has unique user/company. Slot booking uses a one-to-one interview relation plus row locks. Payment event IDs and provider references are unique. Invoices and entitlements are one-to-one with payments.

Company scoping is enforced in server queries via active memberships. Related application data inherits company from the job. Recruiter-supplied company is a scoped form queryset, and editing a job cannot switch its company. Pending guest applications are withheld from recruiters until email verification. Revoked memberships and suspended companies stop access immediately.

Indexes support company/status jobs, job/stage/application chronology, candidate chronology, audit organization/action timestamps and task queues. List screens use pagination; CSV caps at 5,000. Candidate fact normalization and full structured qualification tables in the blueprint remain future migrations. Existing extraction sections are unverified source text, not certified candidate facts.

Production roles: migration owner for schema changes, runtime role for domain data, audit append-only permission, backup role. The supplied deployment must be hardened to restrict audit UPDATE/DELETE and privileged data access. PostgreSQL RLS is not implemented; application-level isolation is tested. Do not claim database RLS isolation is active.

Apply with `python manage.py migrate`. Detect drift using `makemigrations --check --dry-run`. CI starts PostgreSQL 16. Local checks reported separately; PostgreSQL CI results must be inspected after push. Store money in minor units and timestamps in UTC. Display defaults to Asia/Qatar. SQLite is forbidden by production settings.
