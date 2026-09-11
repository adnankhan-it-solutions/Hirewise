# Privacy and data handling

Status: engineering design, not a legal determination. Public policy copy is a development draft. Qatar counsel must approve controller identity, purposes/lawful bases, special-nature data treatment, provider contracts, retention, rights deadlines, transfers and incident obligations.

Account: name, verified email, password hash, role, MFA secret encrypted for administrators. Application: candidate-supplied name/email, letter, screening answer, URL, private CV, consent version/purpose/time, vacancy association and lifecycle history. Extracted text remains separate from originals. Matching stores source IDs, policy/version, explanation and unknowns. No demographics, passport, scraping, brokers or advertising collection.

Company members can see verified applications only for authorized companies. Candidates see their own fields, public stage history and interview answers, never internal notes/rationale. Guest email links establish a two-hour application-scoped session and can be recovered by email. A verified candidate may claim a guest application through a matching-email verification link. Identity merging is never performed merely from an unverified form value.

Privacy centre records access/correction/export/deletion requests. Candidate self-export excludes internal third-party records. Admin workflow tracks review and resolution; marking fulfilled requires actually fulfilling the request. `enforce_retention` previews eligible unsuccessful/withdrawn/archived records; `--execute` deletes private objects and derived content, scrubs identity and retains minimal lifecycle evidence. Legal holds prevent this. Account-level deletion, broader legal-hold UI, audit PII minimization review and provider/backup erasure verification remain launch work.

Default 180 days is a configurable engineering value, not a Qatar legal retention rule. Do not enable automatic execution until the policy is approved. Backups are encrypted, access restricted and expire according to the approved schedule; restored backups must replay deletion tombstones before service resumes. Objects with versioning need lifecycle/purge rules for older versions.

External AI is currently off, and no document is sent to an AI service. A provider agreement, approved regions, minimization, no unrelated training and notice updates are required before activation. Public GitHub Pages contains no application records or intake forms; GitHub infrastructure may log visitor IPs for security.
