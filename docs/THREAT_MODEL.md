# Threat register

Likelihood/impact below are initial qualitative assessments before production verification. Owner for all unassigned controls is the platform operator until a named security owner is appointed. Residual risk remains open until tested in the deployment environment.

| Threat / attack | Likelihood | Impact | Prevention | Detection | Response / residual work |
|---|---|---|---|---|---|
| Candidate data breach through public object access | Medium | Critical | Private bucket, quarantine, authorization, short session-bound download tokens | Storage access logs and synthetic access probes | Block bucket, rotate grants, scope exposure; live bucket policy verification pending |
| Recruiter account takeover / stuffing | High | High | Argon2, strong passwords, login limits, email verification | Login-failure audit events and shared counter metrics | Suspend account, revoke sessions; optional recruiter MFA and risk detection pending |
| Administrator compromise | Medium | Critical | Mandatory encrypted TOTP, replay protection, separate admin role | Admin action audit and alerts | Revoke sessions/keys, forensic review; MFA recovery/step-up design pending |
| Broken tenant isolation / IDOR | Medium | Critical | Query scope from membership/job, UUIDs, negative tests | Access-denied events and penetration tests | Disable affected route, inspect access; RLS is not implemented |
| Malicious CV / parser resource exhaustion | High | High | Type/signature/size/archive limits, scanner, bounded subprocess | Quarantine/task error states, queue age alerts | Quarantine, patch scanner/parser; real scanner/isolated image test pending |
| CV prompt injection | High | High | No tools or AI currently; conservative instruction flag and no score on suspicious text | Suspicious-content warning | Human review; future LLM schema/evidence defenses need independent evaluation |
| SQL injection | Medium | High | Parameterized ORM, no raw user SQL | Security testing/error metrics | Patch, assess scope, rotate DB credentials if necessary |
| Stored/reflected XSS | High | High | Escaped templates, no HTML-rich user content, CSP | Browser/CSP reports and tests | Remove executable exposure, rotate sessions; external report collector pending |
| CSRF | Medium | High | CSRF on browser writes, no GET mutations, SameSite | 403 request events | Inspect bypass, patch, revoke sessions |
| SSRF from profile URL | Medium | High | Candidate URLs never fetched; provider destinations controlled by deployment | Egress monitoring | Block egress, rotate exposed metadata credentials |
| Privilege escalation / role tampering | Medium | Critical | Registration role allowlist, server gates, admin MFA, owner billing/team scope | Role/action audit, tampering tests | Suspend accounts and restore grants |
| Payment amount/redirect manipulation | High | High | Server price snapshots, exact signed event verification, no redirect trust | Failed webhook/reconciliation metrics | Hold entitlement and reconcile; real provider absent |
| Webhook spoofing / replay | High | High | HMAC/timestamp/unique IDs/terminal state in internal sandbox | Invalid-event counts | Rotate key, review ledger; merchant-specific signing still unimplemented |
| AI data leakage | Medium | Critical | External AI disabled, provider approval and minimization required | Egress/provider audit | Disable integration and assess disclosure; production AI architecture remains unfinished |
| Insecure backups / malicious admin | Medium | Critical | Restricted encrypted backups, separation of roles, external immutable audit target | Access reviews, restore drills | Revoke grants, restore evidence; external controls not provisioned |
| Dependency / CI compromise | Medium | Critical | Pinned Python packages, pip-audit, least-permission Actions, tests before Pages deploy | CI audits and change review | Freeze deployments, rebuild trusted artifacts; pin action/image digests during release hardening |
| Sensitive logging | Medium | High | Route names/correlation IDs only, raw Django URL logs suppressed, no CV/AI payload logging | Log sampling and secret scans | Restrict/purge according to policy, rotate any exposed tokens |
| Retention / deletion failure | Medium | High | Explicit expiry, legal hold, reviewed retention command, derived-content erasure | Preview counts, tombstone audit, backup expiry checks | Retry purge; account deletion and full backup tombstone replay remain unfinished |

Production sign-off requires a dated test/evidence link for each control, a named owner, and explicit acceptance of remaining risks. This table is not a penetration-test report.
