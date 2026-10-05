# Eilo Implementation Plan

## Current merged baseline 5 October 2026

CR-2026-10-05-01 was authorized by the owner: finalize the ripple/results design and merge it into the project. Eilo Visual Interaction Design v2.0 is authoritative for updated visual/search/outside-app behavior; the following historical material does not override it. Core inference and all conversation history/derived memory remain local. Optional confirmed live search is a new external query flow, not cloud conversation inference. No app code, provider provisioning, device pass or deployment is implied.

- Home now uses a blue/light-purple theme and rounded centre-out ripples during listening/speaking; stopped/standby/thinking remain truthful and distinct. Accessible Start/Stop, Memory and Settings remain available.
- Spoken response text is the default fallback; rich cards show enabled text/images/videos with attribution and explicit media playback. Recommended initial defaults: text on, images/video off.
- Visual cards expire after20 seconds of actual inactivity after speech/processing/loading/video/interaction; pin and dismiss are explicit. The existing60-second conversation timer remains independent. Lock/Stop/privacy transitions clear personal display state.
- Android outside-app overlay requires separate opt-in, special permission and physical-device feasibility. iOS has a generic notification fallback; rich results may require opening Eilo. No generic cross-platform Siri overlay or guaranteed notification timeout. Locked surfaces remain generic.
- Search off by default, per-query preview/confirmation and minimized approved payload only; no transcript/memory/account ID/location history upload, no query/results in Neon or service logs. Provider/media licensing, retention, cost and real-device cache inspection block release until resolved.
- GitHub selected public initially/private later. Actions, EAS, Vercel and native test distribution remain the recommended stack subject to integration gates. Human task review, staging authorization and production/store approval remain separate.
- JSON backlog1.5 contains175 tasks across23 groups, including26 additions; design approval does not authorize their implementation. The2October UX approval is reconciled in JSON and CSV; old pending wording is historical.


## Historical baseline through 2 October 2026


Current revision:2October2026 · Neon account database and authentication direction authorized; detailed implementation design awaiting review. Historical phase/approval statements below do not describe current completion.

Version 1.0 · Approved 2 October 2026 Australia Melbourne · R01 inventory completed; app development not started

This plan follows the approved Product Specification v1.0 and Architecture v1.0. It completes stage 5 of the supplied workflow, planning. It defines small reviewable tasks, dependencies, verification and human approval gates. The owner approved the plan and the initial R01 readiness task on 2 October 2026. Authorization remains task-scoped; later coding, installations, experiments and deployment require their defined approval gates.

The first objective is to establish whether the approved experience is feasible on both Android and iOS before building the complete product. Screen-off CPU conversation and protected local history are the principal risks. A task may pass as an engineering experiment while demonstrating that a product target cannot be met; this is recorded as a feasibility failure and cannot become an automatic approval to continue the affected scope.

## 1 Work and approval rules

1. Execute only the next explicitly authorized task. Approval of this overall plan does not automatically authorize every task.
2. Before starting, state the task ID, intended outcome, boundaries, dependencies and verification. Do not ask again if that exact task is already authorized.
3. Make one coherent change or experiment. Use an isolated branch/checkpoint and avoid unrelated refactors. If a task expands beyond one reviewable outcome, split it and present the revised boundary before continuing.
4. Verify the behaviour changed by the task. Use meaningful tests for privacy, state transitions and failures; do not create tests that merely duplicate trivial implementation details.
5. Present the result and stop: changed files/diff, evidence, any failures, limitations, and the proposed next task. Do not execute that next task until the user approves it. Work inside a running task can proceed autonomously, including fixing failures within its authorized scope.
6. Keep prototypes and synthetic fixtures separate from product code until explicitly reviewed. Reusing experiment code in production requires a reviewed integration task.
7. Do not change the approved product constraints, upload personal data, install tracking SDKs, enable cloud fallback, or add accounts to overcome a technical blocker.
8. Deployment, store submission and real-user pilot access have separate approval gates, even after development is complete.

Approval is supplied in this conversation, for example: “Approve F03 and start F04.” Agent self-review and automated checks support human review; they do not replace the user’s decision. A passed test is not approval.

## 2 Readiness and dependencies

R01 checked the accessible Linux workspace: no app repository/source project, Android SDK/NDK commands or native compiler commands were found; Node/npm and a Java runtime are available. macOS/Xcode and physical-device access are not established. See Eilo Readiness Check R01 for evidence and limitations. Do not assume that the current workspace can compile or run iOS or access physical phones.

| Dependency | Needed for | Handling if unavailable |
|---|---|---|
| Authorized repository or agreed new repository location | Versioned code and review checkpoints | Establish during R01; do not create an external repository without authorization |
| macOS with compatible Xcode and signing configuration | iOS native builds and real-device background tests | Document the gap; no simulator-only claim of iOS feasibility |
| Compatible Android SDK/NDK/JDK and build tools | Native Android builds | Install only in an authorized setup task; never expose signing credentials |
| Physical Android and iPhone test devices | Lock, thermal, microphone, CPU and battery evaluation | Mark gates blocked; do not substitute desktop benchmarks |
| Approved model/runtime/voice artifact licenses | Downloading, packaging and redistribution | Resolve the exact artifact terms before inclusion |
| Tested key/crypto and storage APIs | Locked writes and authenticated memory | Do not replace with handwritten cryptography or plaintext storage |
| Model-distribution hosting with acceptable logging | Production downloads | Keep early fixtures local; do not silently accept retained per-user access history |

No calendar deadline is promised until R01 establishes available equipment and developer capacity. Task sizes are measured by reviewable outcomes rather than lines of code. Long hardware soak tests should run with progress visibility; lack of tool access is a blocker, not permission to claim results.

## 3 Phase A Preparation

Each row is independently reviewable and requires approval before the next task.

| ID | Scope and deliverable | Depends on | Definition of done |
|---|---|---|---|
| R01 | Read-only readiness inventory: repository/location, available toolchain, devices, signing requirements and missing access | Plan and R01 approval | An evidence-based readiness checklist; no installs, scaffolding or app code; missing resources identified |
| R02 | Lock the evaluation artifacts: exact model/runtime/voice IDs, revisions, licenses, hashes and packaging needs | R01 | Reproducible candidate manifest; licensing gaps explicit; no claim of production suitability |
| R03 | Create the minimal versioned native/RN harness and local build instructions | R01, R02 | Clean builds launch on both available platforms; no microphone capture, history, account or analytics; missing physical builds clearly blocked |

R03 is the first task that may create application code and install necessary dependencies, only when explicitly authorized. It must remain a minimal harness, not a prebuilt full app.

## 4 Phase B Feasibility experiments

Prioritize the iOS background risk early. All audio/content is synthetic or generated for testing. Capture is transient; test measurements contain no real-user conversation content.

| ID | One experiment and deliverable | Depends on | Definition of done |
|---|---|---|---|
| F01 | iOS native user-started audio session: capture, playback, background/lock, Stop, interruption and route handling | R03 | Physical-device evidence for each lifecycle state; no JS keepalive or recorded audio files; unresolved policy limitations documented |
| F02 | Android native microphone service with notification Stop and lifecycle handling | R03 | Physical-device background/lock and termination evidence; capture never precedes consent; no automatic boot/force-stop revival claim |
| F03 | English wake phrase and native turn detection | F01, F02 | Synthetic activation/no-activation set evaluated on both platforms; combined phrase/question not lost; no ambient transcription/history; initial accuracy/false-trigger results reported |
| F04 | Local conversation model CPU-only benchmark: Qwen3-1.7B and 0.6B candidates | R02, R03 | Correct non-thinking configuration, synthetic prompt quality review, first-token/prefill timing and peak memory; run during permitted background operation as well as foreground |
| F05 | Moonshine native streaming ASR evaluation | R02, F01, F02 | Synthetic speech recognition results across agreed conditions; verify streaming path, timing and memory on both platforms |
| F06 | Installed offline system TTS evaluation; Kokoro deferred | R02, F01, F02 | Actual mobile first-audio/generation speed and voice review; packaging/license verified; no inferred full-app latency |
| F07 | One generic spoken turn combining wake, ASR, CPU reply and TTS; no persistent history | F03–F06 | End-to-end meaningful-audio delay and interruption results on both platforms; offline operation; stage breakdown, failures and initial 10-minute thermal observations |
| F08 | Screen-off feasibility soak of the experiment: active conversation and standby | F07 | Defined 60-minute active and eight-hour standby trials on agreed devices; battery, latency distributions, memory, heat and wake availability reported against approved budgets |

F08 may be split into separate device/workload runs at review, rather than requiring one oversized diff. A repeat is justified by a changed configuration or failed measurement, not by a desire to keep testing indefinitely.

### Feasibility decision gate

Before building memory and full product features, present a decision report covering both platforms. Record each supported device/configuration as pass, fail or not tested. No simulator or laptop result qualifies as a physical-device pass.

- If background execution is unavailable or iOS usage cannot be justified under platform rules, stop the affected path and request a reviewed scope/platform decision.
- If the smaller model improves latency but fails conversational quality, do not present it as a successful replacement.
- If first-token timing looks fast but complete spoken replies miss the target, report the complete result.
- Candidate substitutions within the approved architecture can be proposed; changes to privacy, retention, platform scope or promised behaviour require spec review.

No claim of App Store approval is made until actual review. Record a technical/policy risk assessment here, not a guaranteed acceptance result.

## 5 Phase C Protected local memory

Start only after the feasibility decision gate and relevant task approval. Keep the storage/key work independently testable before connecting live conversation.

| ID | Scope and deliverable | Depends on | Definition of done |
|---|---|---|---|
| M01 | Validate platform key protection and authenticated memory-session lifecycle | Feasibility decision, R03 | Keys usable only under the agreed policy; lock invalidates copied-key access paths; no JS keys; unsupported API/device conditions reported |
| M02 | SQLCipher store and encrypted journal/temporary-store configuration | M01 | Synthetic data inaccessible without keys; inspect actual database/journal/temp paths; close/clear on lock; no plaintext indexes |
| M03 | Sealed inbox for locked-screen writes and authenticated unlocked import | M01, M02 | Vetted crypto composition and API review; ciphertext-only writes while locked; decryption denied; integrity failures rejected; interrupted import is deduplicated |
| M04 | Minimal session/message schema, private-mode write policy and provenance links | M02, M03 | Synthetic history persists across restart; private turns create no persistent data; interrupted reply status is represented correctly |
| M05 | Retention, delete-one/delete-all, dependent-memory invalidation and 250 MB quota | M04 | Controlled-clock expiry tests, no recall of expired data, cascade deletion, key reset/inbox removal, quota reservations and disk-full failures; no silent mode change |
| M06 | Minimal local fact/text retrieval and correction | M04, M05 | Cross-session recall set passes the agreed rubric; uncertain facts identified; deletion/private-mode isolation preserved; bounded prompts use untrusted memory text |
| M07 | Backup and device-transfer exclusion audit | M01–M06 | Actual backup/restore/transfer inspection on supported platforms finds no recoverable personal history, inbox or keys; no login restoration path |

If the sealed-inbox composition cannot satisfy the approved locked write/read separation, stop M03. Do not keep the main database decryptable while locked as a shortcut. Physical deletion timing follows available maintenance opportunities; clarify any stricter deadline before changing that policy.

## 6 Phase D Product integration

| ID | Scope and deliverable | Depends on | Definition of done |
|---|---|---|---|
| P01 | Production native controller with states, generation cancellation and privacy epochs | F07, M01–M04 | Deterministic state/cancellation tests; stale callbacks cannot play private output or commit private-mode data; controller independent of JS UI |
| P02 | Connect memory/retrieval to conversation and enforce locked generic mode | P01, M05–M07 | Unlocked authorized memory works; lock cancels old private context/output; wake speech cannot retrieve saved memories or perform destructive actions |
| P03 | Minimal RN Home and settings/onboarding controls | P01, P02 | Start/Stop, accurate state, English/guest flow, separate consent/private mode; no hidden listening, sign-up or cloud service |
| P04 | Authenticated Memory UI and local correction/deletion controls | P03, M06 | Pagination/accessibility, safe lock transitions, no JS persistent content; storage warnings and corrective choices work |
| P05 | Model-pack installation/update manager with signed manifest and rollback | R02, P03 | Allowlisted asset downloads, verification before activation, interrupted-download recovery, version compatibility and no personal network payloads |
| P06 | Conversation/safety behaviour evaluation and narrowly scoped fixes | P02–P05 | Human-reviewed multi-turn and safety rubric; honest AI/uncertainty behaviour; fixes tested for regressions without adding remote inference |

P03 or P04 may be divided into separate screen tasks if the diff is difficult to review. P05 starts with local fixtures; production hosting setup is separately authorized when a concrete hosting choice and logging policy are reviewable.

## 7 Phase E Verification and release preparation

| ID | Scope and deliverable | Depends on | Definition of done |
|---|---|---|---|
| V01 | Map and run specification acceptance criteria A01–A21 | P01–P06 | Each requirement has a scenario, evidence and pass/fail/not-tested result; defects become separate approved fix tasks |
| V02 | Inspect complete app storage, traffic, logs, backup, UI snapshots and lock/epoch races | V01 | No unauthorized persistence/transmission; synthetic-marker inspection supplemented with encryption/format/network analysis; unresolved privacy issues block release |
| V03 | Full supported-device performance, quality and sustained-use verification | V01, V02 | Cold/warm and foreground/screen-off distributions, approved workload and budgets; final support list backed by physical-device evidence |
| V04 | Prepare reviewable release package and pilot plan | V02, V03 | Dependency/license inventory, signing/build provenance, privacy disclosures, known limitations, model distribution policy, rollback and defect handling documented |

A privacy review should be independent where feasible, especially for the sealed-inbox/key composition. No second agent or third-party reviewer is assumed authorized; arrange any external review explicitly. Automatic tests cannot certify the complete security claim.

After V04, the owner separately approves a private pilot or store submission. App Store/Play review outcomes, rollout and observation belong to later workflow stages. Public deployment and real-user data collection are not included in this plan’s execution permission.

## 8 Evidence and definition of done

Every task completion report contains:

- Task ID, intended user behaviour and exact scope completed.
- Relevant diff/files and reproducible verification steps.
- What ran, on which environment/device and model revision, with results. “Not run” is explicit and never replaced with an assumed pass.
- Privacy implications, remaining limitations and failures.
- Checkpoint/commit identifier where a repository exists; do not merge/publish without applicable authorization.
- The next task proposed for approval.

A task is done when its scoped deliverable is reviewable, required checks have meaningful evidence, and blockers are explained. The user’s acceptance closes its review gate. Do not leave a failed test concealed because the demonstration appeared to work.

### Requirement coverage

Evidence links are added only when verification actually runs. All acceptance criteria also receive full-app verification in V01 and the applicable privacy/performance gates.

| Spec requirements | Primary tasks |
|---|---|
| F01–F03: permissions, states, standby activation | F01–F03, P01, P03 |
| F04–F08: context, voice interaction, relevance, tone and clarification | F04–F07, M06, P02, P06 |
| F09–F12: interruption, self-trigger prevention, context limits and Stop | F03, F07, P01, P02 |
| F13–F15: offline use, readiness and no unsolicited/restarted listening | F07, P01, P03, P05 |
| F16: local memory controls | M02–M06, P04 |
| F17–F18: background and locked-screen rules | F01, F02, F08, M01, M03, P02 |
| F19: backup/transfer exclusions | M07, V02 |
| S01–S04: no egress/leakage/logging and protected UI | M02, M07, P01–P05, V02 |
| S05–S07: artifact integrity, credentials and no remote accounts | R02, M01, P03, P05, V02 |
| S08: privacy failure blocks release | All tasks, V02, V04 |
| S09–S10: encrypted state, keys and source-aware deletion | M01–M06, P02, V02 |
| A01–A03: permission and wake journey | F01–F03, P03 |
| A04: cross-session/private/deleted memory | M04–M06, P02 |
| A05–A06: interruption and lifecycle | F07, F08, P01, P02 |
| A07–A10: offline, storage, backup and optional-identity verification | M02–M07, P03, P05, V02 |
| A11–A12: routes/readiness and complete measurements | F01, F02, P05, V03 |
| A13–A15: screen-off, termination and privileged actions | F08, M01, M03, P01, P02, P04 |
| A16: no training/upload paths | R02, P05, V02 |

This matrix identifies ownership without implying that any requirement has passed.

## 9 Current status and next authorization

| Workflow stage | Status |
|---|---|
| Idea/problem, research and specification | Product specification v1.0 approved |
| Architecture | Direction v1.0 approved; feasibility still untested |
| Incremental plan | Approved 2 October 2026 |
| R01 readiness inventory | Completed with build/repository/device blockers; ready for review |
| Implementation and experiments | Not started |
| Verification, staging, deployment and observation | Not started |

R01 is complete as a read-only inventory, with readiness blockers documented. The proposed next task is **R02, the evaluation artifact/runtime manifest**. R02 can proceed independently of missing phones or Xcode once authorized. R03 remains the first code-writing/setup task and requires its own approval and an agreed repository/environment path. App coding, model inference and physical-device tests have not started.

## Reference documents

- Eilo MVP Specification v1.0, approved 1 October 2026.
- Eilo Architecture v1.0, approved for planning 1 October 2026.
- Supplied Production Vibe Coding workflow: plan, small build loop, verification, human review and later release gates.

This plan introduces no new model-performance claims. Exact dependency/platform information is verified again when execution begins because releases and permissions can change.



## Current account and privacy baseline — 2 October 2026

The owner authorized Neon PostgreSQL for minimal account persistence and authentication, retaining social sign-in and device-local conversation history. This replaces the earlier no-user-database/stateless-relay proposal. The implementation design below is ready for review; no database, hosted service or app has been provisioned.

### Selected architecture

**Database:** Neon PostgreSQL. **Authentication:** Better Auth service backed by Neon PostgreSQL, with email/password and Google, plus Apple on iOS. Keep guest conversation equally usable and free. Select pinned versions at the native feasibility task; native capture/inference remains outside authentication. Better Auth's documented React Native route uses its Expo integration. Assess Expo modules/custom native development builds in the React Native project; Expo Go is insufficient for the voice engine. Do not assume compatibility before device tests.

Neon's managed authentication (currently documented as Managed Better Auth) stores users/sessions/auth configuration in Postgres, but its roadmap lists web frameworks and Google/GitHub/Vercel providers, not React Native or Apple. Therefore the implementation route is a separately hosted Better Auth service using Neon as its Postgres database. Hosting provider selection is pending. It is not claimed that Neon hosts this custom service. Do not silently substitute another database or remove Apple to use managed auth. Reassess managed auth only if documented native/provider support meets the requirements. PostgreSQL stores identity; it is not itself an authentication protocol.

Native app → HTTPS auth/account service → Neon PostgreSQL. Apple/Google authenticate through native/system flows. No SQL connection string, owner credential, server secret or raw database access in the mobile bundle. An account API verifies the authenticated session and derives the subject server-side. Enforce per-user access plus least-privileged database roles; test denied cross-account reads/updates. RLS may add defence in depth, but must be explicitly configured and tested rather than assumed.

### Minimal account data contract

| Data | Persistence and purpose |
|---|---|
| Immutable account ID | Remote identity and authorization |
| Verified email and verification state | Email access, recovery and account communication |
| Name/display name | Optional, editable, no legal-name requirement |
| Creation/update timestamp | Account lifecycle only, no conversation activity timestamps |
| Provider identity links | Framework-managed provider/subject; no email-only automatic merging |
| Password hash, sessions and verification records | Framework-managed lifecycle data, never plaintext passwords; bounded expiry/cleanup |
| Provider tokens where required | Sensitive lifecycle secrets, minimize scopes/retention, restrict access and use documented framework encryption/key handling |
| Account consent/privacy version | Minimal record of the account disclosure accepted; local history/background choices remain local |

Use the auth library's generated schema/migrations rather than inventing table names or directly editing managed internals. Application profile extensions refer to the immutable auth user ID. Avoid duplicate email/name copies where the auth user record already provides them. Document exact required fields after pinning the implementation version. No profile photo ingestion, location, contacts, advertising IDs, chat timestamps, emotions, audio, transcripts, facts, embeddings, prompts, local keys or personal models in Neon. No conversation tables, history-upload API, object-store archive or training pipeline in this release.

### Authentication journeys and account lifecycle

- Optional email sign-up/sign-in plus Google, and Apple on iOS. Display privacy disclosure before account creation. Optional name may be edited later. Verified-email policy, verification resend, reset and recovery are handled by the auth service; messages never include conversational data. Account forms may require typing; core conversation does not. Rate-limit/enumeration protections, session expiry, CSRF/nonce/redirect rules, password validation and secure cookie/device credential storage are tested before release.
- First use: optional identity choice or skip → explicit local-history consent → optional background consent/readiness → Home stopped. The review prototype may open on Home; it is not first-install routing evidence. A separate welcome page remains unimplemented, as discussed and accepted. Returning users open Home with actual native state.
- Sign-in, password reset and social success never start capture, grant history consent, recover history or unlock Memory. Use separate device authentication for personal data and privacy changes. Auth outage/expiry/revocation leaves offline guest conversation usable. Do not treat cached identity as authorization to a remote API.
- Normal sign-out requires local authentication, stops capture/context, clears this device's identity/session and preserves encrypted local memory with disclosure. Different-identity switching requires local authentication and explicit destructive reset before association; no automatic email linking. Framework account linking is disabled until a separately authenticated explicit linking flow is designed.
- Remote account deletion requires fresh account reauthentication; local personal-data deletion separately requires device authentication. Revoke all Eilo sessions, remove profile/identity/verification records under the approved retention policy and revoke provider grants where supported. Delete current-device personal state only after explicit local confirmation. Other devices cannot be remotely wiped; on confirmed account invalidation they close identity and require local reset before a different identity links. Offline local history remains device-protected and cannot be claimed remotely erased.
- Offline deletion: stop and erase local personal state if confirmed, show remote account deletion/revocation pending, retain only the minimum protected retry state until resolution. Never display remote success before service confirmation. Provide in-app status/retry and an authenticated public web deletion path for users who uninstalled the app. Delete Eilo's account, not the person's Apple/Google account.

### Retention, privacy and operations

Active account records persist until account deletion or until no longer needed for the declared purpose. Proposed active-system deletion target: within7 days of a verified request; sessions revoked promptly. Backup/point-in-time recovery/replica/branch retention and vendor logs require a documented finite schedule before launch. The7-day target does not claim immediate removal from backups. Restore must reapply deletion records so deleted accounts do not reappear. Keep only narrowly justified deletion/security records with explicit purpose and expiry; no indefinite account-event history. A precise backup horizon and deletion-proof method remain implementation/release gates.

Account PII exists in Neon, auth infrastructure, email delivery and provider systems. Review region availability, cross-border access/subprocessors, contracts, provider logging, retention and incident response. An Australian DB region alone does not establish Australian-only processing. Encrypt transport and storage, keep secrets/keys separately controlled, prevent credential/request-body logging and redact necessary operational diagnostics. Do not promise “no retained auth information”: users, sessions, verification and provider links are deliberately retained for authentication. No behavioural analytics or conversation telemetry.

Neon branches/backups can duplicate identity/session data. Production data must not be cloned into developer/preview branches. Use isolated synthetic accounts, distinct OAuth credentials and least-privileged CI access. Tests cover migrations, authorization, session lifecycle, deletion, restore, connection pooling, cold starts and service costs. Free conversation does not mean free account hosting/auth/email/model distribution.

Australian regulatory assessment: basic account storage is not inherently prohibited. Applicability depends on entity/business scope, including turnover and exceptions such as health-service provision. Do not rely on a startup exemption without assessment. The applicable requirements include collection necessity/notice, permitted use, access/correction, security, retention/deletion, overseas disclosures and breach response. The app remains casual adult conversation, not claimed mental-health treatment. Legal/privacy assessment and actual provider contracts are release gates, not completed legal clearance.

Cloud conversation history is technically possible but not approved. Encryption at rest with server-held keys still allows the service to read content. A later optional client-side end-to-end encrypted backup could reduce server content exposure but requires a separate key/recovery, consent, deletion and multi-device design. Do not add even ciphertext history to Neon in this release. No personal training uploads.

### Consolidated review and evidence

| Area | Position |
|---|---|
| Original vision | Friendly free voice conversation first; calls/camera/app actions and live browsing deferred |
| Models | Moonshine Small Streaming; Qwen3 1.7B Q4_K_M CPU evaluation; installed offline system TTS. Kokoro deferred |
| Preparation | Moonshine verified; Qwen source/environment verified, conversion unfinished; RAM note deferred |
| Local memory | Explicit consent, encrypted local text/derived data,90-day default,250MB personal store; private sessions save nothing |
| Background/lock | Explicit opt-in, platform-native lifecycle; generic locked conversation; native feasibility unproven |
| UI | Eilo / I am here for you; warm-neutral/teal light and dark; simulated account/voice/privacy screens |
| Evidence | Earlier18 synthetic prototype groups and22 palette pair checks; no real OAuth/database/native/security/participant pass |
| Primary risk | Real-phone quality/latency/battery and iOS background availability; protected locked-memory composition |
| Account tradeoff | Identity/recovery of account access provides no conversation recovery. Destructive identity switching needs usability review |
| Document correction | Current system TTS replaces old Kokoro recommendations; later decisions supersede historical approval wording; current check report controls counts |

### Sources and pending verification

Verified2October2026; publisher docs establish available integrations, not measured Eilo performance:
- Neon auth overview: https://neon.com/docs/auth/overview
- Neon supported frameworks/providers: https://neon.com/docs/auth/roadmap
- Neon production requirements: https://neon.com/docs/auth/production-checklist
- Better Auth native integration: https://better-auth.com/docs/integrations/expo
- Better Auth Apple: https://better-auth.com/docs/authentication/apple
- Better Auth PostgreSQL: https://better-auth.com/docs/adapters/postgresql
- OAIC small business: https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/organisations/small-business
- OAIC APP3 collection: https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-3-app-3-collection-of-solicited-personal-information
- OAIC APP8 overseas disclosure: https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-8-app-8-cross-border-disclosure-of-personal-information
- OAIC APP11 security/retention: https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information

User authorization covers this account-storage direction and document revision. Review the detailed service/native integration, retention/deletion and privacy design before its implementation task. No application development, infrastructure creation, credentials, database migrations or deployment occurs in this documentation task.

## Revised delivery sequence

First authorize one DEVOPS setup task and reconcile equipment/signing readiness; then run existing native/audio/model/security feasibility tasks. VIS foreground work follows controller readiness; SEARCH provider assessment can proceed independently as an explicitly authorized research task. Outside-app SURFACE integration follows native lifecycle evidence and card privacy tests. Release evidence includes new OR06 matrix alongside existing VERIFY gates. No full product scaffold or implementation is authorized by this documentation merge.
