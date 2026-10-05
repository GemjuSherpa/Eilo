# Eilo feature sprint plan

5 October 2026 — VC-DEVOPS-01 setup deliverable; awaiting owner review.

Local Android Studio/Gradle and Xcode builds are the primary pathway. No paid services, paid upgrades or spending are authorized. GitHub/Vercel/Neon free tiers may be evaluated within their limits; this setup creates only GitHub resources. No application scaffold, dependency installation, service provisioning or device experiment is included.

Sprints are ordered feature increments with no committed dates or velocity estimates. They are not blanket execution approval. Select one dependency-ready task at a time, verify its acceptance criteria, present evidence and stop for human review. S00 preserves historical design acceptance, not Design 2.0/native verification.

All 175 stable task IDs and dependency edges are preserved. The existing source is Eilo_Codex_Knowledge_Transfer; the root docs/baseline path is currently absent. Future native feasibility, Apple capabilities/signing, provider licensing/retention and physical-device access remain gates. Optional features are planned, not removed to satisfy the zero-paid-service constraint.

| Sprint | Goal | Tasks |
|---|---|---|
| S00 | Accepted historical UX baseline | 14 |
| S01 | Repository, board and build foundation | 7 |
| S02 | Controller, cancellation and permission gates | 11 |
| S03 | Model preparation and verified installation | 10 |
| S04 | Guest consent and native audio lifecycle | 16 |
| S05 | Wake detection, turn boundaries and recognition | 10 |
| S06 | Local reply generation and offline speech | 12 |
| S07 | Safe generic conversation integration | 7 |
| S08 | Physical-device voice feasibility decision | 6 |
| S09 | Protected keys and generic locked operation | 8 |
| S10 | Encrypted history, retention and deletion | 10 |
| S11 | Sealed locked-write inbox | 3 |
| S12 | Local recall and protected continuity integration | 12 |
| S13 | Optional accounts and lifecycle | 17 |
| S14 | Accessible visual conversation and cards | 10 |
| S15 | Confirmed search and safe media | 6 |
| S16 | Outside-app surfaces and native visual acceptance | 6 |
| S17 | Integrated privacy, performance and failure verification | 8 |
| S18 | Build distribution and release readiness | 2 |

## S00 — Accepted historical UX baseline

- VC-UX-01 — UX brief and navigation (dependencies: none; baseline: approved)
- VC-UX-02 — Voice interaction specification (dependencies: VC-UX-01; baseline: approved)
- VC-UX-03 — User journey and state map (dependencies: VC-UX-01;VC-UX-02; baseline: approved)
- VC-UX-04 — Onboarding wireframes (dependencies: VC-UX-03; baseline: approved)
- VC-UX-05 — Home wireframes (dependencies: VC-UX-03; baseline: approved)
- VC-UX-06 — Memory wireframes (dependencies: VC-UX-03; baseline: approved)
- VC-UX-07 — Settings and recovery wireframes (dependencies: VC-UX-03; baseline: approved)
- VC-UX-08 — Interface and privacy copy (dependencies: VC-UX-02;VC-UX-04;VC-UX-05;VC-UX-06;VC-UX-07; baseline: approved)
- VC-UX-09 — Visual tokens and components (dependencies: VC-UX-04;VC-UX-05;VC-UX-06;VC-UX-07; baseline: approved)
- VC-UX-10 — Accessibility and platform adaptations (dependencies: VC-UX-08;VC-UX-09; baseline: approved)
- VC-UX-11 — Clickable UI prototype (dependencies: VC-UX-08;VC-UX-09;VC-UX-10; baseline: approved)
- VC-UX-12 — Prototype usability review (dependencies: VC-UX-11; baseline: approved)
- VC-UX-13 — Design corrections (dependencies: VC-UX-12; baseline: approved)
- VC-UX-14 — Design handoff and approval gate (dependencies: VC-UX-13; baseline: approved)

## S01 — Repository, board and build foundation

- VC-BASE-01 — Versioned Android launch shell (dependencies: none; baseline: planned)
- VC-BASE-02 — Versioned iOS launch shell (dependencies: none; baseline: planned)
- VC-BASE-03 — Native state contract (dependencies: none; baseline: planned)
- VC-VERIFY-01 — Freeze device/workload matrix (dependencies: none; baseline: planned)
- VC-DEVOPS-01 — Repository and board baseline (dependencies: none; baseline: planned)
- VC-BASE-04 — Native adapter substitution (dependencies: VC-BASE-03; baseline: planned)
- VC-DEVOPS-02 — Focused pull request checks (dependencies: VC-DEVOPS-01; baseline: planned)

## S02 — Controller, cancellation and permission gates

- VC-LOCK-07 — Content-free diagnostics (dependencies: VC-BASE-03; baseline: planned)
- VC-CTRL-01 — Deterministic state transitions (dependencies: VC-BASE-03;VC-BASE-04; baseline: planned)
- VC-CTRL-02 — Stop transaction (dependencies: VC-CTRL-01; baseline: planned)
- VC-CTRL-03 — Generation cancellation token (dependencies: VC-CTRL-01; baseline: planned)
- VC-CTRL-05 — Idle session timeout (dependencies: VC-CTRL-01; baseline: planned)
- VC-CTRL-08 — Safe restart state (dependencies: VC-CTRL-01; baseline: planned)
- VC-SET-04 — Android permission gate (dependencies: VC-BASE-01;VC-CTRL-01; baseline: planned)
- VC-SET-05 — iOS permission gate (dependencies: VC-BASE-02;VC-CTRL-01; baseline: planned)
- VC-CTRL-04 — Privacy epoch guard (dependencies: VC-CTRL-03; baseline: planned)
- VC-CTRL-06 — End-conversation command (dependencies: VC-CTRL-05; baseline: planned)
- VC-CTRL-07 — Voice Stop command (dependencies: VC-CTRL-02; baseline: planned)

## S03 — Model preparation and verified installation

- VC-PACK-01 — BF16 conversion intermediate (dependencies: none; baseline: planned)
- VC-PACK-03 — Trusted pack manifest schema (dependencies: none; baseline: planned)
- VC-PACK-02 — Q4 conversion artifact (dependencies: VC-PACK-01; baseline: planned)
- VC-PACK-04 — Manifest signature verifier (dependencies: VC-PACK-03; baseline: planned)
- VC-PACK-05 — Model download transport (dependencies: VC-PACK-04; baseline: planned)
- VC-PACK-06 — Artifact hash verifier (dependencies: VC-PACK-05; baseline: planned)
- VC-PACK-10 — Distribution privacy review (dependencies: VC-PACK-05; baseline: planned)
- VC-PACK-07 — Interrupted download recovery (dependencies: VC-PACK-06; baseline: planned)
- VC-PACK-08 — Atomic pack activation (dependencies: VC-PACK-06; baseline: planned)
- VC-PACK-09 — Model readiness gate (dependencies: VC-PACK-08; baseline: planned)

## S04 — Guest consent and native audio lifecycle

- VC-AUDIO-01 — Android foreground capture owner (dependencies: VC-SET-04;VC-CTRL-01; baseline: planned)
- VC-AUDIO-05 — iOS foreground audio owner (dependencies: VC-SET-05;VC-CTRL-01; baseline: planned)
- VC-AUDIO-02 — Android notification Stop (dependencies: VC-AUDIO-01;VC-CTRL-02; baseline: planned)
- VC-AUDIO-04 — Android interruption handler (dependencies: VC-AUDIO-01; baseline: planned)
- VC-AUDIO-07 — iOS interruption handler (dependencies: VC-AUDIO-05; baseline: planned)
- VC-AUDIO-08 — Private audio route guard (dependencies: VC-AUDIO-01;VC-AUDIO-05; baseline: planned)
- VC-SET-01 — Guest onboarding disclosure (dependencies: VC-BASE-01;VC-BASE-02;VC-UX-14; baseline: planned)
- VC-SET-06 — Home Start/Stop control (dependencies: VC-CTRL-02;VC-SET-04;VC-SET-05;VC-UX-14; baseline: planned)
- VC-SET-02 — History consent setting (dependencies: VC-SET-01;VC-UX-14; baseline: planned)
- VC-SET-03 — Background consent setting (dependencies: VC-SET-01;VC-UX-14; baseline: planned)
- VC-SET-08 — Settings volume control (dependencies: VC-SET-06;VC-UX-14; baseline: planned)
- VC-SET-07 — Private-session selector (dependencies: VC-SET-02;VC-CTRL-04;VC-UX-14; baseline: planned)
- VC-AUDIO-03 — Android background consent enforcement (dependencies: VC-AUDIO-01;VC-SET-03; baseline: planned)
- VC-AUDIO-06 — iOS background consent enforcement (dependencies: VC-AUDIO-05;VC-SET-03; baseline: planned)
- VC-AUDIO-09 — Android locked audio feasibility (dependencies: VC-AUDIO-03;VC-AUDIO-04; baseline: planned)
- VC-AUDIO-10 — iOS locked audio feasibility (dependencies: VC-AUDIO-06;VC-AUDIO-07; baseline: planned)

## S05 — Wake detection, turn boundaries and recognition

- VC-TURN-01 — Bounded standby audio buffer (dependencies: VC-CTRL-01; baseline: planned)
- VC-TURN-02 — Wake detector adapter (dependencies: VC-TURN-01; baseline: planned)
- VC-TURN-03 — Wake-plus-question handoff (dependencies: VC-TURN-02; baseline: planned)
- VC-TURN-07 — Self-playback rejection (dependencies: VC-TURN-02; baseline: planned)
- VC-TURN-09 — Wake accuracy trial (dependencies: VC-TURN-02; baseline: planned)
- VC-TURN-04 — Endpoint detector (dependencies: VC-TURN-03; baseline: planned)
- VC-TURN-05 — Streaming ASR adapter (dependencies: VC-TURN-04; baseline: planned)
- VC-TURN-08 — Confirmed-speech interruption (dependencies: VC-CTRL-03;VC-TURN-04; baseline: planned)
- VC-TURN-06 — Recognition clarification (dependencies: VC-TURN-05; baseline: planned)
- VC-TURN-10 — ASR quality trial (dependencies: VC-TURN-05; baseline: planned)

## S06 — Local reply generation and offline speech

- VC-VOICE-01 — Offline voice readiness contract (dependencies: VC-BASE-03; baseline: planned)
- VC-VOICE-02 — Android offline system TTS adapter (dependencies: VC-VOICE-01;VC-BASE-01; baseline: planned)
- VC-VOICE-03 — iOS offline system TTS adapter (dependencies: VC-VOICE-01;VC-BASE-02; baseline: planned)
- VC-VOICE-06 — Offline voice quality trial (dependencies: VC-VOICE-02;VC-VOICE-03; baseline: planned)
- VC-VOICE-04 — Clause-to-speech queue (dependencies: VC-VOICE-02;VC-VOICE-03;VC-CTRL-03; baseline: planned)
- VC-VOICE-05 — Playback progress contract (dependencies: VC-VOICE-04; baseline: planned)
- VC-LLM-01 — In-process CPU model adapter (dependencies: VC-PACK-02;VC-PACK-09; baseline: planned)
- VC-LLM-02 — Non-thinking template configuration (dependencies: VC-LLM-01; baseline: planned)
- VC-LLM-03 — Prompt context budget (dependencies: VC-LLM-02; baseline: planned)
- VC-LLM-06 — CPU model comparison trial (dependencies: VC-LLM-01;VC-LLM-02; baseline: planned)
- VC-LLM-04 — Untrusted memory section (dependencies: VC-LLM-03; baseline: planned)
- VC-LLM-05 — Bounded continuation (dependencies: VC-LLM-03; baseline: planned)

## S07 — Safe generic conversation integration

- VC-BEHAV-01 — AI identity and supportive persona (dependencies: VC-LLM-02; baseline: planned)
- VC-BEHAV-02 — Uncertainty and capability boundaries (dependencies: VC-BEHAV-01; baseline: planned)
- VC-BEHAV-03 — Imminent-danger response policy (dependencies: VC-BEHAV-01; baseline: planned)
- VC-BEHAV-04 — Pre-speech clause policy (dependencies: VC-BEHAV-01;VC-BEHAV-02;VC-BEHAV-03;VC-VOICE-04; baseline: planned)
- VC-JOIN-01 — One offline generic spoken turn (dependencies: VC-TURN-05;VC-LLM-03;VC-VOICE-04;VC-BEHAV-04; baseline: planned)
- VC-JOIN-02 — Spoken follow-up session (dependencies: VC-JOIN-01;VC-TURN-03;VC-CTRL-05; baseline: planned)
- VC-JOIN-03 — Interrupt-and-replace turn (dependencies: VC-JOIN-01;VC-TURN-07;VC-TURN-08; baseline: planned)

## S08 — Physical-device voice feasibility decision

- VC-VERIFY-02 — Meaningful-audio latency trial (dependencies: VC-VERIFY-01;VC-JOIN-01; baseline: planned)
- VC-VERIFY-03 — Interruption latency trial (dependencies: VC-VERIFY-01;VC-JOIN-03; baseline: planned)
- VC-GATE-01 — Generic foreground60min feasibility (dependencies: VC-VERIFY-01;VC-JOIN-02; baseline: planned)
- VC-GATE-02 — Generic screen-off60min feasibility (dependencies: VC-VERIFY-01;VC-JOIN-02;VC-AUDIO-09;VC-AUDIO-10; baseline: planned)
- VC-GATE-03 — Generic standby8h feasibility (dependencies: VC-VERIFY-01;VC-TURN-02;VC-AUDIO-09;VC-AUDIO-10; baseline: planned)
- VC-GATE-04 — Generic companion feasibility decision (dependencies: VC-GATE-01;VC-GATE-02;VC-GATE-03;VC-VERIFY-02;VC-VERIFY-03;VC-TURN-09;VC-TURN-10;VC-LLM-06;VC-VOICE-06; baseline: planned)

## S09 — Protected keys and generic locked operation

- VC-KEY-01 — iOS protected key provider (dependencies: VC-BASE-02; baseline: planned)
- VC-KEY-02 — Android protected key provider (dependencies: VC-BASE-01; baseline: planned)
- VC-INBOX-01 — Vetted sealing composition review (dependencies: VC-KEY-01;VC-KEY-02; baseline: planned)
- VC-KEY-03 — Authenticated memory session (dependencies: VC-KEY-01;VC-KEY-02;VC-CTRL-04; baseline: planned)
- VC-KEY-04 — Lock key release (dependencies: VC-KEY-03; baseline: planned)
- VC-LOCK-01 — Generic lock transition (dependencies: VC-CTRL-04;VC-KEY-04; baseline: planned)
- VC-LOCK-02 — Locked memory/privilege denial (dependencies: VC-LOCK-01;VC-KEY-03; baseline: planned)
- VC-LOCK-03 — Authenticated unlock re-entry (dependencies: VC-LOCK-01;VC-KEY-03; baseline: planned)

## S10 — Encrypted history, retention and deletion

- VC-STORE-01 — SQLCipher store configuration (dependencies: VC-KEY-03;VC-GATE-04; baseline: planned)
- VC-STORE-02 — Final message write (dependencies: VC-STORE-01;VC-SET-07; baseline: planned)
- VC-STORE-07 — Storage quota accounting (dependencies: VC-STORE-01; baseline: planned)
- VC-STORE-03 — Interrupted reply write (dependencies: VC-STORE-02;VC-VOICE-05; baseline: planned)
- VC-STORE-04 — History read pagination (dependencies: VC-STORE-02; baseline: planned)
- VC-STORE-05 — Retention filter (dependencies: VC-STORE-02; baseline: planned)
- VC-STORE-08 — History write reservation (dependencies: VC-STORE-07;VC-STORE-02; baseline: planned)
- VC-STORE-09 — Delete source transaction (dependencies: VC-STORE-02; baseline: planned)
- VC-STORE-06 — Retention physical cleanup (dependencies: VC-STORE-05; baseline: planned)
- VC-STORE-10 — Delete-all key reset (dependencies: VC-STORE-09;VC-CTRL-04; baseline: planned)

## S11 — Sealed locked-write inbox

- VC-INBOX-02 — Public-key sealed write (dependencies: VC-INBOX-01;VC-SET-07;VC-STORE-07; baseline: planned)
- VC-INBOX-03 — Authenticated inbox import (dependencies: VC-INBOX-02;VC-STORE-02; baseline: planned)
- VC-INBOX-04 — Inbox expiry and reset (dependencies: VC-INBOX-02;VC-STORE-05;VC-STORE-10; baseline: planned)

## S12 — Local recall and protected continuity integration

- VC-MEM-01 — Provenance-linked confirmed facts (dependencies: VC-STORE-02; baseline: planned)
- VC-MEM-02 — Bounded lexical retrieval (dependencies: VC-MEM-01;VC-STORE-05;VC-STORE-09; baseline: planned)
- VC-MEM-03 — Fact correction (dependencies: VC-MEM-01;VC-KEY-03; baseline: planned)
- VC-MEM-04 — Memory UI review (dependencies: VC-STORE-04;VC-MEM-01;VC-SET-06;VC-UX-14; baseline: planned)
- VC-LOCK-05 — Android backup/transfer exclusions (dependencies: VC-STORE-01;VC-INBOX-02;VC-KEY-02; baseline: planned)
- VC-LOCK-06 — iOS backup/transfer exclusions (dependencies: VC-STORE-01;VC-INBOX-02;VC-KEY-01; baseline: planned)
- VC-MEM-05 — Memory UI corrective actions (dependencies: VC-MEM-03;VC-MEM-04;VC-STORE-09;VC-STORE-10;VC-UX-14; baseline: planned)
- VC-MEM-06 — Recall quality trial (dependencies: VC-MEM-02;VC-MEM-03; baseline: planned)
- VC-LOCK-04 — Private UI snapshot protection (dependencies: VC-MEM-04;VC-LOCK-01;VC-UX-14; baseline: planned)
- VC-BEHAV-05 — Multi-turn quality trial (dependencies: VC-BEHAV-04;VC-MEM-02; baseline: planned)
- VC-JOIN-04 — Unlocked history integration (dependencies: VC-JOIN-02;VC-STORE-03;VC-MEM-02;VC-KEY-03; baseline: planned)
- VC-JOIN-05 — Locked generic/inbox integration (dependencies: VC-JOIN-01;VC-INBOX-03;VC-INBOX-04;VC-LOCK-01;VC-LOCK-02;VC-LOCK-03; baseline: planned)

## S13 — Optional accounts and lifecycle

- VC-AUTH-01 — Neon/native auth feasibility and provider configuration (dependencies: VC-UX-14; baseline: not_started)
- VC-AUTH-02 — Optional identity screen (dependencies: VC-AUTH-01; baseline: not_started)
- VC-AUTH-03 — Apple native identity adapter (dependencies: VC-AUTH-01; baseline: not_started)
- VC-AUTH-04 — Google native identity adapter (dependencies: VC-AUTH-01; baseline: not_started)
- VC-AUTH-05 — Better Auth account service (dependencies: VC-AUTH-01; baseline: not_started)
- VC-AUTH-06 — Secure identity credential storage (dependencies: VC-AUTH-03;VC-AUTH-04;VC-AUTH-05; baseline: not_started)
- VC-AUTH-13 — Neon identity schema/migrations (dependencies: VC-AUTH-01;VC-AUTH-05; baseline: planned)
- VC-AUTH-07 — Offline expiry and revocation state (dependencies: VC-AUTH-06; baseline: not_started)
- VC-AUTH-08 — Authenticated sign-out (dependencies: VC-AUTH-06; baseline: not_started)
- VC-AUTH-10 — Remote account deletion and provider revocation (dependencies: VC-AUTH-06;VC-AUTH-05; baseline: not_started)
- VC-AUTH-14 — Account API authorization (dependencies: VC-AUTH-13; baseline: planned)
- VC-AUTH-15 — Email sign-up verification and recovery (dependencies: VC-AUTH-05;VC-AUTH-13; baseline: planned)
- VC-AUTH-09 — Identity switch and reset (dependencies: VC-AUTH-08; baseline: not_started)
- VC-AUTH-11 — Identity privacy and store disclosures (dependencies: VC-AUTH-02;VC-AUTH-10; baseline: not_started)
- VC-AUTH-16 — Account retention deletion and restore (dependencies: VC-AUTH-10;VC-AUTH-13; baseline: planned)
- VC-AUTH-17 — Provider/privacy release assessment (dependencies: VC-AUTH-13;VC-AUTH-16; baseline: planned)
- VC-AUTH-12 — Provider integration verification (dependencies: VC-AUTH-03;VC-AUTH-04;VC-AUTH-05;VC-AUTH-07;VC-AUTH-08;VC-AUTH-09;VC-AUTH-10;VC-AUTH-11;VC-AUTH-14;VC-AUTH-15;VC-AUTH-16;VC-AUTH-17; baseline: not_started)

## S14 — Accessible visual conversation and cards

- VC-VIS-01 — Controller driven ripple states (dependencies: VC-CTRL-01; baseline: planned)
- VC-VIS-03 — Spoken response text fallback (dependencies: VC-CTRL-01; baseline: planned)
- VC-VIS-02 — Accessible motion and theme tokens (dependencies: VC-VIS-01; baseline: planned)
- VC-VIS-04 — Independent display preferences (dependencies: VC-SET-07; baseline: planned)
- VC-VIS-05 — Result card selection and sources (dependencies: VC-VIS-03;VC-VIS-04; baseline: planned)
- VC-VIS-09 — Platform navigation and accessible controls (dependencies: VC-VIS-04; baseline: planned)
- VC-VIS-06 — Visual inactivity controller (dependencies: VC-VIS-05; baseline: planned)
- VC-VIS-08 — User initiated media playback (dependencies: VC-VIS-05; baseline: planned)
- VC-VIS-07 — Pin dismiss and stale result cancellation (dependencies: VC-VIS-06; baseline: planned)
- VC-VIS-10 — Visual memory and snapshot boundary (dependencies: VC-VIS-07; baseline: planned)

## S15 — Confirmed search and safe media

- VC-SEARCH-01 — Provider license privacy and cost assessment (dependencies: none; baseline: planned)
- VC-SEARCH-02 — Explicit search authorization and query preview (dependencies: VC-SEARCH-01;VC-VIS-04; baseline: planned)
- VC-SEARCH-03 — Ephemeral query gateway (dependencies: VC-SEARCH-02; baseline: planned)
- VC-SEARCH-04 — Untrusted result normalization (dependencies: VC-SEARCH-03; baseline: planned)
- VC-SEARCH-05 — Safe media retrieval (dependencies: VC-SEARCH-04;VC-VIS-08; baseline: planned)
- VC-SEARCH-06 — Offline and budget fallback (dependencies: VC-SEARCH-04; baseline: planned)

## S16 — Outside-app surfaces and native visual acceptance

- VC-SURFACE-03 — iOS supported surface feasibility (dependencies: VC-AUDIO-10; baseline: planned)
- VC-SURFACE-01 — Android overlay feasibility (dependencies: VC-AUDIO-09;VC-VIS-05; baseline: planned)
- VC-SURFACE-02 — Android overlay presentation (dependencies: VC-SURFACE-01;VC-VIS-07;VC-VIS-10; baseline: planned)
- VC-SURFACE-04 — iOS generic notification fallback (dependencies: VC-SURFACE-03;VC-VIS-10; baseline: planned)
- VC-SURFACE-05 — Outside app lock and consent enforcement (dependencies: VC-SURFACE-02;VC-SURFACE-04; baseline: planned)
- VC-SURFACE-06 — Native visual acceptance matrix (dependencies: VC-VIS-10;VC-SEARCH-06;VC-SURFACE-05; baseline: planned)

## S17 — Integrated privacy, performance and failure verification

- VC-VERIFY-04 — Foreground60min active trial (dependencies: VC-VERIFY-01;VC-JOIN-02; baseline: planned)
- VC-VERIFY-06 — Screen-off8h standby trial (dependencies: VC-VERIFY-01;VC-TURN-02;VC-AUDIO-09;VC-AUDIO-10; baseline: planned)
- VC-VERIFY-09 — Resource-failure safety trial (dependencies: VC-JOIN-04;VC-STORE-08; baseline: planned)
- VC-VERIFY-05 — Screen-off60min active trial (dependencies: VC-VERIFY-01;VC-JOIN-05;VC-AUDIO-09;VC-AUDIO-10; baseline: planned)
- VC-VERIFY-07 — Offline network/privacy audit (dependencies: VC-JOIN-04;VC-JOIN-05;VC-PACK-05; baseline: planned)
- VC-VERIFY-08 — Persistence/backup privacy audit (dependencies: VC-JOIN-05;VC-LOCK-04;VC-LOCK-05;VC-LOCK-06;VC-LOCK-07; baseline: planned)
- VC-VERIFY-10 — Requirement evidence closure (dependencies: VC-VERIFY-07;VC-VERIFY-08;VC-AUTH-12; baseline: planned)
- VC-VERIFY-11 — Release package preparation (dependencies: VC-VERIFY-10;VC-PACK-10; baseline: planned)

## S18 — Build distribution and release readiness

- VC-DEVOPS-03 — Mobile build signing and staging (dependencies: VC-DEVOPS-02; baseline: planned)
- VC-DEVOPS-04 — Owner controlled release gates (dependencies: VC-DEVOPS-03; baseline: planned)

Verification: task count 175; unique stable IDs 175; all dependencies in the same or an earlier sprint. Same-sprint tasks must still follow dependency order. Detailed requirements, focused tests and historical evidence remain in baseline JSON v1.5.

Current Git exception: owner authorizes setup Git operations only in repositories newly created for this task. Existing repositories must not be accessed. The exception does not authorize later implementation, deployment or publication.
