# Text interviews

Current flow is recruiter-approved text interviewing with human assessment. Recruiter writes 1–10 job-related questions and an explicit rubric before invitation. Candidate reads the disclosure, consents, reserves a future company slot and can save responses after the slot begins. UTC timestamps render in Asia/Qatar by default. Submitted interviews become read-only to candidates. Recruiter records a score and explanation with underlying question/answer snapshots. Assessment versions are append-only.

No recording, facial analysis, emotion inference, accent scoring or automatic hiring decisions. No external AI is configured. `InterviewProvider` defines an adapter boundary; AI question drafting and structured AI assessment remain unimplemented until a reviewed provider, minimization and schema/evidence validation are added. Human reports are labelled human.

Known remaining requirements: automated reminder job, candidate UI for rescheduling after initial reservation, configurable slot expiry/duration enforcement, advanced competency scoring, scheduling concurrency verification on production PostgreSQL, and optional future official calendar integration. Audio/video/transcription are explicitly future scope and cost zero in the current model.

Invitations preserve application data on outages. Email uses the durable outbox. Guest candidates can recover access through `/applications/recover/`. Candidate account/guest authorization gates every interview request, answer update and underlying report.
