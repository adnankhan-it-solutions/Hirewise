# HTTP interface

Server-rendered application with cookie sessions and CSRF-protected forms. UUID routes are not access controls. Successful form writes generally redirect; validation errors render the form or return 400; unauthenticated protected pages redirect to login; role mismatch 403; unauthorized scoped records 404; conflict 409; throttling 429. Private replies use no-store and noindex.

| Routes | Methods | Access |
|---|---|---|
| `/`, `/jobs/`, `/jobs/{id}/`, `/pricing/`, `/pages/{page}/` | GET | Public |
| `/accounts/register/`, `/accounts/login/` | GET/POST | Public with throttling |
| `/accounts/verify/{token}/` | GET confirm / POST consume | Expiring token + CSRF |
| `/accounts/logout/` | POST | Current session |
| `/accounts/mfa/` | GET/POST | Authenticated admin |
| `/dashboard/` | GET | Verified account; admin also MFA |
| `/portal/company/new/`, `/portal/jobs/new/`, `/portal/jobs/{id}/edit/` | GET/POST | Verified scoped recruiter |
| `/portal/jobs/{id}/action/` | POST | Scoped recruiter |
| `/jobs/{id}/apply/` | GET/POST multipart | Guest or verified candidate; production intake gate |
| `/applications/guest/{id}/{token}/` | GET/POST | Single-use token |
| `/applications/recover/` | GET/POST | Throttled email recovery |
| `/applications/{id}/` | GET/POST note | Candidate/guest owner; recruiter within company |
| `/applications/{id}/transition/` | POST | Candidate withdrawal or scoped human recruiter |
| `/documents/{id}/`, `/documents/download/{signed}/` | GET | Authorized session, clean scan, expiry/hash check |
| `/applications/{id}/rescreen/` | POST | Scoped recruiter |
| `/applications/{id}/report/` | GET | Scoped recruiter; audited |
| `/interviews/{id}/` | GET/POST | Scoped recruiter reads; owning candidate answers |
| `/interviews/{id}/assess/` | POST | Scoped human recruiter |
| `/portal/checkout/{job}/`, `/portal/payments/{id}/`, `/portal/invoices/{id}/` | GET/POST as applicable | Company owner |
| `/integrations/sandbox/webhook/` | POST JSON | Raw-body HMAC + timestamp; see PAYMENTS.md |
| `/portal/admin/*` | GET/POST as applicable | Verified admin + MFA |
| `/portal/privacy/export/` | GET JSON attachment | Own verified candidate |
| `/health/` | GET JSON | Public DB readiness only |

No public candidate API, bearer API key system or third-party integration API is enabled. The production API's external contract/versioned OpenAPI specification remains future integration work.
