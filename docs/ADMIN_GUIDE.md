# Administrator guide

Create the first administrator through `python manage.py create_admin email` using an interactive strong password. The command refuses to promote an existing account. Login requires time-based authenticator enrollment; the stored secret is encrypted. There is no default password or open Django admin URL. Use a secured operational procedure for lost MFA; self-service recovery is not yet implemented.

Dashboard shows aggregate counts and pending company/privacy review. Approve/suspend a company with a reason. Job moderation is separate: review vacancy content and company approval before publishing. Paid publication requires a verified live entitlement when payments_required is enabled; the sandbox cannot satisfy it.

Configuration controls working platform name/contact/legal fields, currency, notice version, retention days, blind review and feature availability. Existing historical policy/payment snapshots are not rewritten. Add packages under Pricing (integer minor units). Audit views are read-only and paginated. Privacy queue records review/resolution; do not mark fulfilled until actual work is done. Production intake is not exposed as a generic settings toggle.

Pending target controls include comprehensive user/session administration, special justified candidate-support access, legal-document version editor, advanced AI templates/configuration, invoice/refund administration and immutable backup/audit dashboards. These must be implemented before claiming the complete platform-owner capability set.
