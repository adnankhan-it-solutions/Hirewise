# Backup and recovery runbook

Target production RPO <=24 hours and RTO <=8 hours initially; these are objectives, not verified guarantees. Require automated managed PostgreSQL backups plus an independent encrypted export, encrypted private-object backup/versioning and protected secrets recovery. Configure region, retention and access under legal review. Do not keep the only backup in the same failure domain or under the same routinely used admin credential.

Daily procedure: use a restricted backup role, `pg_dump --format=custom` to a private temporary volume; encrypt the output with the organization's approved key manager before transfer; upload to private immutable storage with retention and integrity metadata; clear local plaintext; alert on failure. Never put database URLs/passwords into a committed script or logs. Object backup uses provider replication/export with private ACLs, encryption and lifecycle rules for current and non-current versions.

Restore drill: choose a backup, restore into an isolated empty staging PostgreSQL using `pg_restore --no-owner --no-privileges`, restore private objects into a new private bucket, restore only staging-specific application secrets, run migrations if appropriate, replay post-backup deletion/anonymization tombstones, verify record counts, tenant boundaries, document hashes and application history, then record elapsed restore time and evidence. Do not send production notifications or call payment/AI endpoints from a restored test environment.

Before traffic switch, verify role grants, revoked credentials/sessions, audit continuity, malware scan state, webhook reconciliation and object privacy. Owner-authorized production recovery must have a rollback plan. A successful database import alone is not a complete recovery test.

No production hosting, backup job or restoration has been provisioned/tested in this workspace. Local SQLite checks are not evidence of PostgreSQL disaster recovery. These operational launch gates remain open.
