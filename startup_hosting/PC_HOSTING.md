# Hosting Hirewise directly on this PC

This mode runs the complete Django application from the current PC without Docker. Devices on the same local network can use `http://10.40.23.128:8000` while the PC is powered on and connected at that address.

## Commands

From the repository root:

```sh
startup_hosting/setup_pc.sh
startup_hosting/start_pc.sh
startup_hosting/status_pc.sh
startup_hosting/stop_pc.sh
```

`setup_pc.sh` creates a private `.env.pc` with random secrets, applies migrations, builds static assets and creates synthetic demo records if none exist. The environment file, process ID and logs are excluded from Git.

The server binds to all network interfaces on port 8000. This allows LAN access but does not bypass the PC firewall, router or institutional network policy. If another device cannot connect, verify it is on the same network and that inbound TCP 8000 is allowed. Do not disable the firewall wholesale.

## Current PC-mode limitations

- HTTP is used on the LAN. Passwords and candidate information are not protected against network interception. Use only synthetic test data until HTTPS is configured.
- SQLite is used locally. It persists in `db.sqlite3`, but is unsuitable for concurrent public production use.
- Local private document storage is used and is not encrypted independently from the PC disk.
- ClamAV is not installed, so CVs remain quarantined and cannot be processed/downloaded.
- The console email backend writes verification/reset links to a restricted local log; it does not send real email.
- This address is private and is not reachable from the public internet.

For actual applicant use, install the `startup_hosting/compose.yaml` stack on this PC or another server with PostgreSQL, MinIO, ClamAV and HTTPS. Public internet access additionally needs a domain plus router port forwarding to Caddy, or a reviewed authenticated tunnel. Never expose Django/Gunicorn port 8000 directly to the internet.
