# Eilo feature backlog — v1.5

Current baseline:5 October2026. UX owner approval recorded; Design2.0 and CR-2026-10-05-01 supersede old theme and display exclusions. Historical task text below is retained; JSONv1.5 governs current requirements/status. App implementation and native verification have not started.

2 October 2026 · Australia/Melbourne

This maps the approved requirements to 23 feature groups and 175 single-responsibility tasks. It is a development/review backlog, not authorization to implement the whole app. The owner deferred outstanding verification to development; no new build or test ran while preparing this backlog.

## UI/UX design phase — added in version1.1

Product UI implementation requires approved `VC-UX-14` handoff. Native shell/audio/model/security feasibility experiments may use minimal synthetic test controls without the product design gate. Design approval is required for product onboarding, Home, Settings, Memory and private UI surfaces.

Voice UX defines cues/wording/turn behaviour; a clickable prototype simulates it and cannot establish wake accuracy, latency, screen-off feasibility or privacy enforcement. Design1.2 wireframes/layouts, visual system, interactive prototype and handoff are now complete for owner review. Native feasibility and participant usability are not validated.

| Task | Deliverable | Depends on |
|---|---|---|
| VC-UX-01 | UX brief and navigation | Approved specification |
| VC-UX-02 | Voice interaction specification | VC-UX-01 |
| VC-UX-03 | User journey and state map | VC-UX-01, VC-UX-02 |
| VC-UX-04 | Onboarding wireframes | VC-UX-03 |
| VC-UX-05 | Home wireframes | VC-UX-03 |
| VC-UX-06 | Memory wireframes | VC-UX-03 |
| VC-UX-07 | Settings and recovery wireframes | VC-UX-03 |
| VC-UX-08 | Interface and privacy copy | VC-UX-02, VC-UX-04, VC-UX-05, VC-UX-06, VC-UX-07 |
| VC-UX-09 | Visual tokens and components | VC-UX-04, VC-UX-05, VC-UX-06, VC-UX-07 |
| VC-UX-10 | Accessibility and platform adaptations | VC-UX-08, VC-UX-09 |
| VC-UX-11 | Clickable UI prototype | VC-UX-08, VC-UX-09, VC-UX-10 |
| VC-UX-12 | Prototype usability review | VC-UX-11 |
| VC-UX-13 | Design corrections | VC-UX-12 |
| VC-UX-14 | Design handoff and approval gate | VC-UX-13 |

### VC-UX-01 — UX brief and navigation

- **Requirements:** F05, F13, F16, F17
- **Done when:** Define adult English guest audience, Home/Memory/Settings navigation and design constraints.
- **Review/check:** Review brief against approved spec; optional identity per amendment; no conversation cloud or transcript-first requirement.

### VC-UX-02 — Voice interaction specification

- **Requirements:** F02, F07, F08, F09, F10, F12, F15
- **Done when:** Define cues and spoken wording for standby/activation/listening/thinking/speaking/clarification/interruption/Stop/silence.
- **Review/check:** Walk scripted turns including screen-off use; distinguish operational cues from meaningful reply latency and prohibit unsolicited chat.

### VC-UX-03 — User journey and state map

- **Requirements:** F01, F04, F16, F17, F18, A01, A04, A06, A13, A15
- **Done when:** Map first setup, normal dialogue, private mode, consented background, lock/unlock and memory correction/deletion.
- **Review/check:** Every branch has visible/spoken state and next action; no hidden consent or unauthenticated personal recall.

### VC-UX-04 — Onboarding wireframes

- **Requirements:** F01, F13, F14, F16, F17, S07
- **Done when:** Wireframe English guest setup, model/voice readiness and separate history/background/microphone choices.
- **Review/check:** Review denial/missing models/no offline voice/local history loss; no implied background consent.

### VC-UX-05 — Home wireframes

- **Requirements:** F02, F05, F09, F12, F15
- **Done when:** Wireframe central Start/Stop and all native status variants without requiring typed chat.
- **Review/check:** Review fresh stopped/standby/capturing/thinking/speaking/paused/error/reconnected states; Stop remains reachable.

### VC-UX-06 — Memory wireframes

- **Requirements:** F16, F18, S04, S10
- **Done when:** Wireframe authenticated paginated history/facts, correction, delete-source and delete-all.
- **Review/check:** Review auth denial/empty/deleted/expired/interrupted states; destructive actions require explicit authenticated screen flow.

### VC-UX-07 — Settings and recovery wireframes

- **Requirements:** F05, F14, F16, F17, F18, A11, N10
- **Done when:** Wireframe private session, history consent/retention, background consent, voice/volume and bounded recovery screens.
- **Review/check:** Review storage-full/headphone-disconnect/permission-revoked/unsupported-background cases; no silent private switch/cloud fallback.

### VC-UX-08 — Interface and privacy copy

- **Requirements:** F07, F08, F14, F16, F17, F18, S04
- **Done when:** Draft concise screen labels, disclosures, errors and voice prompts matching approved capabilities.
- **Review/check:** Review no emotion diagnosis/emergency action/current facts guarantee; notifications and locked feedback disclose no history.

### VC-UX-09 — Visual tokens and components

- **Requirements:** F02, F05
- **Done when:** Define typography, colour, spacing, icons, focus/disabled/error states and component variants for both platforms.
- **Review/check:** Review component sheet; state meaning never relies on colour alone and OS mic indicators remain honest.

### VC-UX-10 — Accessibility and platform adaptations

- **Requirements:** F05, F17, S04
- **Done when:** Specify screen-reader labels/order, text scaling, touch targets, contrast, reduced motion and non-audio cues; Android/iOS differences.
- **Review/check:** Review accessibility scenarios and contrast measurements; OS conventions/system controls retained.

### VC-UX-11 — Clickable UI prototype

- **Requirements:** F01, F02, F05, F16, F18
- **Done when:** Build a design-only prototype of reviewed journeys with synthetic content and simulated voice/lock/error states.
- **Review/check:** Click through setup/start/stop/private/memory/lock/recovery; simulation is labelled, with no real capture/model or personal persistence.

### VC-UX-12 — Prototype usability review

- **Requirements:** F05, F16, F17, F18
- **Done when:** Run and document task-based review of prototype; identify scoped revisions and remaining uncertainty.
- **Review/check:** Review finding evidence for consent comprehension, stopping, listening state and memory deletion; no invented participant outcomes or recruitment/messages without authorization.

### VC-UX-13 — Design corrections

- **Requirements:** F05, F16, F17, F18
- **Done when:** Resolve reviewed usability issues within approved product scope and annotate prototype changes.
- **Review/check:** Repeat affected walkthroughs only; unresolved issues stay visible and scope changes require separate approval.

### VC-UX-14 — Design handoff and approval gate

- **Requirements:** F02, F05, F16, F17, F18, S04
- **Done when:** Deliver versioned screen/component/state/voice specifications mapped to existing build tasks and obtain human design approval.
- **Review/check:** Owner reviews concrete prototype/spec; pending or rejected design blocks product-screen implementation; no automatic approval.

**Changed product-task dependencies:** VC-SET-01, VC-SET-02, VC-SET-03, VC-SET-06, VC-SET-07, VC-SET-08, VC-MEM-04, VC-MEM-05, VC-LOCK-04. All prior task IDs and recorded statuses are retained. Each design task follows the existing one-task/review/approval loop.

**Current design status:** VC-UX-01 to VC-UX-13 artifacts/checks are complete for owner review; VC-UX-14 handoff exists but its human approval gate is pending. See Companion_Design_Handoff.md, Companion_Prototype.html, Companion_Design_Review.md and check evidence. The user authorized this design batch; app implementation remains unstarted.

## Current baseline

Moonshine asset integrity, Qwen source integrity and the isolated conversion environment are recorded as preparation evidence. No app implementation, Qwen conversion, runtime inference or physical-device validation is complete. RAM capacity remains deferred:10.5GB available vs16GB proposed starting allocation. Offline system voices replace Kokoro for the initial prototype; Kokoro remains deferred.

## How Codex should execute

1. Select one authorized task whose dependencies are approved; state its ID and boundary. Do not begin unrelated tasks.
2. Use one reviewable commit/change. Implement only that responsibility; use fakes/adapters for unavailable downstream components.
3. Run the focused test and relevant regression checks during development. Record environment/device, fixtures, outcome and evidence. A task with tests not run is not verified.
4. Report behaviour, diff, test evidence and limitations. Mark `awaiting_review`; stop for human approval before the next task.
5. If scope expands, split it. Failed tests become narrowly scoped fixes; preserve stable IDs and original traceability.
6. Deployment, hosting and store submission need their own concrete review and authorization. Backlog approval does not authorize every build task.

Independent testing means an item has a controllable input, observable outcome and isolated test boundary. It does not mean every feature can ship independently or has zero prerequisites. Platform tests remain separate from shared logic tests. Interface-only tasks do not require all real model adapters.

## Feature index

| Feature | Responsibility | Tasks |
|---|---|---:|
| UX | UI/UX design and approval | 14 |
| BASE | Build foundation | 4 |
| CTRL | Conversation state and cancellation | 8 |
| SET | Guest setup and consent | 8 |
| PACK | Generic model preparation and installation | 10 |
| AUDIO | Platform audio lifecycle | 10 |
| TURN | Activation and turn boundaries | 10 |
| LLM | Local reply generation | 6 |
| VOICE | Offline speech output | 6 |
| KEY | Authenticated local access | 4 |
| STORE | Encrypted local history | 10 |
| INBOX | Locked ciphertext writes | 4 |
| MEM | Local facts and recall | 6 |
| LOCK | Lock transitions and privacy surfaces | 7 |
| BEHAV | Conversation behaviour | 5 |
| JOIN | Small vertical integrations | 5 |
| VERIFY | Development validation and release gates | 11 |
| GATE | Feasibility review before persistent memory | 4 |

## Single-responsibility task cards

Original app tasks remain `planned / implementation not_started / verification not_run / approval not_requested`. UX design tasks now await owner review; their status is authoritative in the JSON and CSV. Requirements use the original F/S/A IDs. N IDs explicitly map approved numerical planning targets. Dependency completion requires review approval; hardware-specific evidence can be blocked while independent shared tasks proceed.

### BASE — Build foundation

#### VC-BASE-01 — Versioned Android launch shell

- **Requirement:** F13, A10.
- **Dependency:** No task prerequisite; relevant environment access and task authorization still required.
- **Boundary:** Android UI shell.
- **Done when:** Launch an empty guest screen without capture, account or network activity.
- **Focused test:** Build/install/launch on Android; inspect manifest permissions and startup traffic.

#### VC-BASE-02 — Versioned iOS launch shell

- **Requirement:** F13, A10.
- **Dependency:** No task prerequisite; relevant environment access and task authorization still required.
- **Boundary:** iOS UI shell.
- **Done when:** Launch an empty guest screen without capture, account or network activity.
- **Focused test:** Build/install/launch on iOS; inspect entitlements and startup traffic.

#### VC-BASE-03 — Native state contract

- **Requirement:** F02, S04.
- **Dependency:** No task prerequisite; relevant environment access and task authorization still required.
- **Boundary:** shared contract.
- **Done when:** State events expose bounded state/error fields and no transcript or keys.
- **Focused test:** Contract fixture rejects personal fields and invalid state codes.

#### VC-BASE-04 — Native adapter substitution

- **Requirement:** F13, S01.
- **Dependency:** VC-BASE-03.
- **Boundary:** test seam.
- **Done when:** Controller can use fake capture, ASR, model, TTS and memory adapters without downloading weights.
- **Focused test:** One synthetic turn uses fakes; assert no real capture, files or network.

### CTRL — Conversation state and cancellation

#### VC-CTRL-01 — Deterministic state transitions

- **Requirement:** F02, F12.
- **Dependency:** VC-BASE-03, VC-BASE-04.
- **Boundary:** native controller.
- **Done when:** Declared events produce one authoritative setup/stopped/standby/capturing/thinking/speaking/paused/error state.
- **Focused test:** Table-driven valid/invalid transition tests with fake adapters.

#### VC-CTRL-02 — Stop transaction

- **Requirement:** F12, F15, A06.
- **Dependency:** VC-CTRL-01.
- **Boundary:** native controller.
- **Done when:** Stop cancels work, releases capture and clears volatile context without deleting committed history.
- **Focused test:** Stop in every active state; delayed adapter completion cannot resume capture/output.

#### VC-CTRL-03 — Generation cancellation token

- **Requirement:** F09, S04, A05.
- **Dependency:** VC-CTRL-01.
- **Boundary:** native controller.
- **Done when:** An invalidated generation cannot enqueue or play later audio.
- **Focused test:** Deliver old tokens/audio after cancellation; output sink remains empty.

#### VC-CTRL-04 — Privacy epoch guard

- **Requirement:** S02, S04, S10.
- **Dependency:** VC-CTRL-03.
- **Boundary:** native controller.
- **Done when:** Stale operations cannot emit private output or commit data after policy invalidation.
- **Focused test:** Race fake completion against lock/private/Stop epochs; reject stale reads/writes/output.

#### VC-CTRL-05 — Idle session timeout

- **Requirement:** F04, F12, A06.
- **Dependency:** VC-CTRL-01.
- **Boundary:** native controller.
- **Done when:** After60s with no speech/processing/playback, session context clears and state returns to standby.
- **Focused test:** Fake-clock test; processing and playback defer timer; finishing playback starts timer.

#### VC-CTRL-06 — End-conversation command

- **Requirement:** F04, F12.
- **Dependency:** VC-CTRL-05.
- **Boundary:** deterministic active command.
- **Done when:** End conversation clears active context and returns to standby while keeping explicitly enabled capture.
- **Focused test:** Active command test distinguishes end-conversation from Stop.

#### VC-CTRL-07 — Voice Stop command

- **Requirement:** F12, A15.
- **Dependency:** VC-CTRL-02.
- **Boundary:** deterministic active command.
- **Done when:** Recognized stop listening invokes the same Stop transaction; no model/tool action required.
- **Focused test:** Inject recognized command; capture releases even if model adapter fails.

#### VC-CTRL-08 — Safe restart state

- **Requirement:** F15, A14.
- **Dependency:** VC-CTRL-01.
- **Boundary:** native persistence boundary.
- **Done when:** Every process launch begins stopped; restored settings never resume microphone capture.
- **Focused test:** Relaunch with prior listening preference and simulate reboot/restore; capture count stays zero.

### SET — Guest setup and consent

#### VC-SET-01 — Guest onboarding disclosure

- **Requirement:** F13, S07, A10.
- **Dependency:** VC-UX-14, VC-BASE-01, VC-BASE-02.
- **Boundary:** React Native screen.
- **Done when:** English adult onboarding describes AI identity, local encrypted text, no saved audio and local-loss limitations; no signup.
- **Focused test:** UI flow reaches setup without account fields or account request.

#### VC-SET-02 — History consent setting

- **Requirement:** F16, S07.
- **Dependency:** VC-UX-14, VC-SET-01.
- **Boundary:** local consent policy.
- **Done when:** History is off until explicit choice; choice is versioned and separate from microphone permission.
- **Focused test:** Fresh setup and permission grant cannot enable history; explicit choice can.

#### VC-SET-03 — Background consent setting

- **Requirement:** F17, A06.
- **Dependency:** VC-UX-14, VC-SET-01.
- **Boundary:** local consent policy.
- **Done when:** Background mode defaults off and changes only through explicit choice.
- **Focused test:** Permission grant or UI exit does not set consent; exercise separate toggle.

#### VC-SET-04 — Android permission gate

- **Requirement:** F01, A01.
- **Dependency:** VC-BASE-01, VC-CTRL-01.
- **Boundary:** Android permission adapter.
- **Done when:** Capture is impossible before user Start plus granted permission; denial does not loop prompts.
- **Focused test:** Permission fake covers not-requested/denied/granted/revoked; capture spy.

#### VC-SET-05 — iOS permission gate

- **Requirement:** F01, A01.
- **Dependency:** VC-BASE-02, VC-CTRL-01.
- **Boundary:** iOS permission adapter.
- **Done when:** Capture is impossible before user Start plus granted permission; denial does not loop prompts.
- **Focused test:** Same permission matrix against iOS adapter; denial leaves settings usable.

#### VC-SET-06 — Home Start/Stop control

- **Requirement:** F02, F05.
- **Dependency:** VC-UX-14, VC-CTRL-02, VC-SET-04, VC-SET-05.
- **Boundary:** React Native screen.
- **Done when:** One accessible control requests Start/Stop and displays actual native state after reconnect.
- **Focused test:** UI test with changed native state while UI detached; no typing required.

#### VC-SET-07 — Private-session selector

- **Requirement:** F16, A04.
- **Dependency:** VC-UX-14, VC-SET-02, VC-CTRL-04.
- **Boundary:** local privacy policy.
- **Done when:** Selected private session blocks every persistent personal write; older history remains unchanged.
- **Focused test:** Fake sinks for transcript/fact/index/inbox receive zero writes; mode race test.

#### VC-SET-08 — Settings volume control

- **Requirement:** F05.
- **Dependency:** VC-UX-14, VC-SET-06.
- **Boundary:** React Native control.
- **Done when:** Accessible volume control affects output gain without altering consent or capture.
- **Focused test:** Output fake asserts gain; screen-reader control test.

### PACK — Generic model preparation and installation

#### VC-PACK-01 — BF16 conversion intermediate

- **Requirement:** S05.
- **Dependency:** No task prerequisite; relevant environment access and task authorization still required.
- **Boundary:** model-build task, verification deferred to development.
- **Done when:** Pinned official Qwen input produces BF16 GGUF with recorded recipe, hash, size and metadata.
- **Focused test:** Execute approved conversion; inspect tensor inventory/tokenizer/template; record RAM check separately.

#### VC-PACK-02 — Q4 conversion artifact

- **Requirement:** S05.
- **Dependency:** VC-PACK-01.
- **Boundary:** model-build task.
- **Done when:** Pinned quantizer produces Q4_K_M with output hash/size and complete provenance.
- **Focused test:** Repeat identical conversion separately and compare; inspect quantization metadata.

#### VC-PACK-03 — Trusted pack manifest schema

- **Requirement:** S05, S06.
- **Dependency:** No task prerequisite; relevant environment access and task authorization still required.
- **Boundary:** native installer contract.
- **Done when:** Manifest declares IDs, revisions, origins, hashes, sizes, licenses and runtime compatibility. License evidence for weights/runtimes/voices/phonemizers and dependencies must be reviewable before any pack inclusion.
- **Focused test:** Reject missing fields, unsafe paths, incompatible versions and unknown algorithms.

#### VC-PACK-04 — Manifest signature verifier

- **Requirement:** S05, S06.
- **Dependency:** VC-PACK-03.
- **Boundary:** native verifier.
- **Done when:** Only manifests signed by configured release trust keys are accepted.
- **Focused test:** Known test key: valid, modified, unknown-key and invalid-signature fixtures.

#### VC-PACK-05 — Model download transport

- **Requirement:** S01, S06, S07.
- **Dependency:** VC-PACK-04.
- **Boundary:** native downloader.
- **Done when:** Only allowlisted HTTPS assets/redirects are requested; downloader accepts no personal payload or stable tracking ID.
- **Focused test:** Fake server checks origin/redirect policy and request schema; reject non-HTTPS/foreign origin.

#### VC-PACK-06 — Artifact hash verifier

- **Requirement:** S05, S06.
- **Dependency:** VC-PACK-05.
- **Boundary:** native installer.
- **Done when:** Incomplete or wrong-hash file never becomes available to inference.
- **Focused test:** Truncation and bitflip fixtures remain quarantined; exact fixture passes.

#### VC-PACK-07 — Interrupted download recovery

- **Requirement:** F14, S05.
- **Dependency:** VC-PACK-06.
- **Boundary:** native installer.
- **Done when:** Interrupted generic download resumes safely or restarts without marking partial data ready.
- **Focused test:** Terminate transfer; resume with changed ETag/content; reverify complete file.

#### VC-PACK-08 — Atomic pack activation

- **Requirement:** F14, S05.
- **Dependency:** VC-PACK-06.
- **Boundary:** native installer.
- **Done when:** Compatible verified pack activates atomically; failed update preserves previous working pack.
- **Focused test:** Crash/failure at activation boundaries; no mixed-version pack reaches runtime.

#### VC-PACK-09 — Model readiness gate

- **Requirement:** F14, A11.
- **Dependency:** VC-PACK-08.
- **Boundary:** native readiness policy.
- **Done when:** Missing/incompatible model or unsupported configuration prevents Start with a clear reason; no cloud fallback.
- **Focused test:** Fake missing/corrupt/unsupported cases keep capture/model calls stopped.

#### VC-PACK-10 — Distribution privacy review

- **Requirement:** S01, S06, S08.
- **Dependency:** VC-PACK-05.
- **Boundary:** production hosting gate.
- **Done when:** Hosting choice has reviewable logging/retention evidence compatible with no retained user access history.
- **Focused test:** Review actual origin/CDN configuration and retention; incompatible/unknown policy blocks hosting release.

### AUDIO — Platform audio lifecycle

#### VC-AUDIO-01 — Android foreground capture owner

- **Requirement:** F01, F17.
- **Dependency:** VC-SET-04, VC-CTRL-01.
- **Boundary:** Android native.
- **Done when:** Capture starts from permitted visible user action and is owned outside JavaScript.
- **Focused test:** Physical Android Start/Stop; JS suspension does not falsify actual capture state.

#### VC-AUDIO-02 — Android notification Stop

- **Requirement:** F02, F12, A15.
- **Dependency:** VC-AUDIO-01, VC-CTRL-02.
- **Boundary:** Android native notification.
- **Done when:** Required ongoing notification shows no personal content and its Stop action releases capture.
- **Focused test:** Tap notification Stop without opening UI; verify mic released.

#### VC-AUDIO-03 — Android background consent enforcement

- **Requirement:** F17, A06.
- **Dependency:** VC-AUDIO-01, VC-SET-03.
- **Boundary:** Android native.
- **Done when:** UI exit stops capture without consent; enabled permitted service can continue.
- **Focused test:** Physical test of both consent states; return UI reads true state.

#### VC-AUDIO-04 — Android interruption handler

- **Requirement:** F12, A06.
- **Dependency:** VC-AUDIO-01.
- **Boundary:** Android native.
- **Done when:** Calls/focus loss/permission revocation/contention safely pause/stop and release volatile state.
- **Focused test:** Inject each OS event independently; no fabricated capture or automatic unsafe restart.

#### VC-AUDIO-05 — iOS foreground audio owner

- **Requirement:** F01, F17.
- **Dependency:** VC-SET-05, VC-CTRL-01.
- **Boundary:** iOS native.
- **Done when:** Permitted user-started native audio session owns capture independently of JavaScript.
- **Focused test:** Physical iPhone start/stop and JS-detached state check.

#### VC-AUDIO-06 — iOS background consent enforcement

- **Requirement:** F17, A06.
- **Dependency:** VC-AUDIO-05, VC-SET-03.
- **Boundary:** iOS native.
- **Done when:** No-consent UI exit stops capture; consented background path uses intended audio mode only.
- **Focused test:** Physical transitions plus entitlement/use-case review; no silent-audio keepalive.

#### VC-AUDIO-07 — iOS interruption handler

- **Requirement:** F12, A06.
- **Dependency:** VC-AUDIO-05.
- **Boundary:** iOS native.
- **Done when:** Interruption/permission loss safely pauses/stops capture and volatile work.
- **Focused test:** Independent native event fixtures and physical call interruption.

#### VC-AUDIO-08 — Private audio route guard

- **Requirement:** F12, A11.
- **Dependency:** VC-AUDIO-01, VC-AUDIO-05.
- **Boundary:** native output policy.
- **Done when:** Headphone/Bluetooth disconnect pauses private output until explicit speaker confirmation.
- **Focused test:** Route event tests show no automatic private speaker playback.

#### VC-AUDIO-09 — Android locked audio feasibility

- **Requirement:** F17, A13, A14.
- **Dependency:** VC-AUDIO-03, VC-AUDIO-04.
- **Boundary:** Android physical experiment.
- **Done when:** Record actual user-started screen-off capture/output availability, termination limits and stopped-state accuracy.
- **Focused test:** Physical lock/Doze/service-kill/reboot matrix; pass/fail/not-tested per configuration.

#### VC-AUDIO-10 — iOS locked audio feasibility

- **Requirement:** F17, A13, A14.
- **Dependency:** VC-AUDIO-06, VC-AUDIO-07.
- **Boundary:** iOS physical experiment.
- **Done when:** Record platform-compliant screen-off capture/output availability and termination limits.
- **Focused test:** Physical lock/background/process-kill matrix; technical evidence and App Review rationale, not approval guarantee.

### TURN — Activation and turn boundaries

#### VC-TURN-01 — Bounded standby audio buffer

- **Requirement:** F03, S02.
- **Dependency:** VC-CTRL-01.
- **Boundary:** native audio buffer.
- **Done when:** Standby retains no more than2s volatile audio; overwritten samples are not saved or transcribed.
- **Focused test:** Fake-clock/sample stream checks max duration; storage/ASR spies remain untouched.

#### VC-TURN-02 — Wake detector adapter

- **Requirement:** F03, A02.
- **Dependency:** VC-TURN-01.
- **Boundary:** native KWS adapter.
- **Done when:** Configured local wake event opens activation; ordinary speech never calls conversational inference.
- **Focused test:** Frozen synthetic wake/nonwake fixtures; fake model call counts.

#### VC-TURN-03 — Wake-plus-question handoff

- **Requirement:** F04, A03.
- **Dependency:** VC-TURN-02.
- **Boundary:** native ASR handoff.
- **Done when:** Relevant bounded audio suffix preserves question immediately after wake phrase without duplicate content.
- **Focused test:** Synthetic combined phrase/question fixture verifies one complete question.

#### VC-TURN-04 — Endpoint detector

- **Requirement:** F08.
- **Dependency:** VC-TURN-03.
- **Boundary:** native VAD/endpoint adapter.
- **Done when:** Active utterance ends through bounded endpoint rules; silence/noise produces no invented utterance.
- **Focused test:** Synthetic pause/noise/overlap fixtures; record endpoint delay separately.

#### VC-TURN-05 — Streaming ASR adapter

- **Requirement:** F05, F08, S01.
- **Dependency:** VC-TURN-04.
- **Boundary:** Moonshine native.
- **Done when:** Only active-turn audio produces bounded partial/final text locally; cancellation removes stale finals.
- **Focused test:** Adapter contract tests with fake audio plus separate native fixture run; no disk audio.

#### VC-TURN-06 — Recognition clarification

- **Requirement:** F08.
- **Dependency:** VC-TURN-05.
- **Boundary:** native input policy.
- **Done when:** Unclear input requests brief clarification and is not promoted to a confirmed memory fact.
- **Focused test:** Unclear/ambiguous/overlap fixture yields clarification and zero confirmed-fact writes.

#### VC-TURN-07 — Self-playback rejection

- **Requirement:** F10, A05.
- **Dependency:** VC-TURN-02.
- **Boundary:** native echo/activation policy.
- **Done when:** Known app playback does not create a wake, transcript or new conversation turn.
- **Focused test:** Playback loopback fixture on speaker/headphones; ASR/model spies show no self-turn.

#### VC-TURN-08 — Confirmed-speech interruption

- **Requirement:** F09, A05, N02.
- **Dependency:** VC-CTRL-03, VC-TURN-04.
- **Boundary:** native interruption policy.
- **Done when:** Confirmed user speech cancels old reply/queued audio; noise alone does not routinely cancel it.
- **Focused test:** Synthetic speech-vs-noise tests with timestamped output sink; device p95 measured later.

#### VC-TURN-09 — Wake accuracy trial

- **Requirement:** N03, A12.
- **Dependency:** VC-TURN-02.
- **Boundary:** separate device measurement.
- **Done when:** Report detection and false activation on frozen quiet and8h ambient datasets by device/route.
- **Focused test:** Actual labelled physical playback trials; retain aggregate counts, no real-user recordings.

#### VC-TURN-10 — ASR quality trial

- **Requirement:** N04, A12.
- **Dependency:** VC-TURN-05.
- **Boundary:** separate device measurement.
- **Done when:** Report WER on frozen English set and accent/name/number/noise slices.
- **Focused test:** Compare final transcripts to synthetic references; explicit failures and sample counts.

### LLM — Local reply generation

#### VC-LLM-01 — In-process CPU model adapter

- **Requirement:** F06, F13, S01.
- **Dependency:** VC-PACK-02, VC-PACK-09.
- **Boundary:** llama.cpp native.
- **Done when:** Verified Q4 model generates tokens locally with CPU-only baseline and cancellation.
- **Focused test:** Synthetic prompt run with all networking blocked; cancellation and load failure fixtures.

#### VC-LLM-02 — Non-thinking template configuration

- **Requirement:** F06.
- **Dependency:** VC-LLM-01.
- **Boundary:** native prompt configuration.
- **Done when:** Actual Qwen chat template disables thinking; no hidden chain is sent to speech.
- **Focused test:** Inspect rendered template/config and synthetic output path; do not rely on prompt wording alone.

#### VC-LLM-03 — Prompt context budget

- **Requirement:** F04, F11, N09.
- **Dependency:** VC-LLM-02.
- **Boundary:** native prompt builder.
- **Done when:** 4096-token context,≤512 recalled tokens and normal≤256 output tokens are enforced deterministically.
- **Focused test:** Token-count fixtures exceed limits; explicit trim policy preserves rules/latest utterance.

#### VC-LLM-04 — Untrusted memory section

- **Requirement:** F06, S10.
- **Dependency:** VC-LLM-03.
- **Boundary:** native prompt boundary.
- **Done when:** Retrieved text cannot replace privileged rules or request tool/privacy actions.
- **Focused test:** Injection-marker memory fixture remains data; no tool/privacy side effects.

#### VC-LLM-05 — Bounded continuation

- **Requirement:** F05, N09.
- **Dependency:** VC-LLM-03.
- **Boundary:** native generation policy.
- **Done when:** Longer requested replies continue only through bounded approved turn chunks without unbounded context growth.
- **Focused test:** Fake long-token stream respects per-chunk and total-context limits.

#### VC-LLM-06 — CPU model comparison trial

- **Requirement:** N05, N08, A12.
- **Dependency:** VC-LLM-01, VC-LLM-02.
- **Boundary:** separate device measurement.
- **Done when:** Report1.7B vs0.6B quality/prefill/first-token/peak memory on supported device proposals.
- **Focused test:** Frozen synthetic prompts; foreground and permitted background CPU runs; no desktop-as-phone claim.

### VOICE — Offline speech output

#### VC-VOICE-01 — Offline voice readiness contract

- **Requirement:** F14, S01, A11.
- **Dependency:** VC-BASE-03.
- **Boundary:** native voice registry.
- **Done when:** No installed offline voice means setup incomplete; network voices are never substituted.
- **Focused test:** Registry fixture with offline/missing/network-only voices returns correct readiness.

#### VC-VOICE-02 — Android offline system TTS adapter

- **Requirement:** F05, S01.
- **Dependency:** VC-VOICE-01, VC-BASE-01.
- **Boundary:** Android native.
- **Done when:** Only installed network-independent voice synthesizes utterances; cancellation clears queued speech.
- **Focused test:** Physical airplane-mode synthesis plus voice flag inspection; capture traffic.

#### VC-VOICE-03 — iOS offline system TTS adapter

- **Requirement:** F05, S01.
- **Dependency:** VC-VOICE-01, VC-BASE-02.
- **Boundary:** iOS native.
- **Done when:** Chosen installed voice works offline and queued utterances can be cancelled.
- **Focused test:** Physical airplane-mode synthesis and network trace; missing-voice fixture fails closed.

#### VC-VOICE-04 — Clause-to-speech queue

- **Requirement:** F05, F09.
- **Dependency:** VC-VOICE-02, VC-VOICE-03, VC-CTRL-03.
- **Boundary:** native output queue.
- **Done when:** Bounded natural clauses play in order and stale/overflow clauses cannot queue indefinitely.
- **Focused test:** Fake token stream and sink verify ordering, bounds and cancellation.

#### VC-VOICE-05 — Playback progress contract

- **Requirement:** F16, A05.
- **Dependency:** VC-VOICE-04.
- **Boundary:** native output metadata.
- **Done when:** Finished/interrupted playback status is available for history without claiming the user heard speech.
- **Focused test:** Stop mid-clause; metadata distinguishes produced/played/interrupted output.

#### VC-VOICE-06 — Offline voice quality trial

- **Requirement:** F05, A12.
- **Dependency:** VC-VOICE-02, VC-VOICE-03.
- **Boundary:** separate device measurement.
- **Done when:** Record installed voice availability, first-audio latency and human intelligibility by platform.
- **Focused test:** Frozen English utterances; measured device timing; no consistent cross-platform identity claim.

### KEY — Authenticated local access

#### VC-KEY-01 — iOS protected key provider

- **Requirement:** S06, S09, F18.
- **Dependency:** VC-BASE-02.
- **Boundary:** iOS native key adapter.
- **Done when:** Device-only nonsynchronizing keys follow approved unlock/authentication policy and never enter JS.
- **Focused test:** Native locked/unlocked/auth-failure key-access tests; inspect configured attributes.

#### VC-KEY-02 — Android protected key provider

- **Requirement:** S06, S09, F18.
- **Dependency:** VC-BASE-01.
- **Boundary:** Android native key adapter.
- **Done when:** Platform-protected wrapped DB keys follow approved unlock/authentication policy and never enter JS.
- **Focused test:** Native auth/lock/key-invalidation tests on baseline OS; unsupported policy blocks.

#### VC-KEY-03 — Authenticated memory session

- **Requirement:** F18, S07.
- **Dependency:** VC-KEY-01, VC-KEY-02, VC-CTRL-04.
- **Boundary:** native authorization.
- **Done when:** Memory access requires current unlocked authenticated session; lock/expiry invalidates it.
- **Focused test:** Fake-clock/lock/auth-denial tests reject reads and privileged writes.

#### VC-KEY-04 — Lock key release

- **Requirement:** S09, F18.
- **Dependency:** VC-KEY-03.
- **Boundary:** native key lifecycle.
- **Done when:** Lock destroys owned decrypted key buffers and closes access, including already-copied key paths.
- **Focused test:** Owned-buffer/access spies plus native security inspection; never claim complete OS RAM erasure.

### STORE — Encrypted local history

#### VC-STORE-01 — SQLCipher store configuration

- **Requirement:** F16, S02, S09.
- **Dependency:** VC-KEY-03, VC-GATE-04.
- **Boundary:** native store.
- **Done when:** DB/WAL/journals are encrypted; temp storage is memory-only; keyless access fails.
- **Focused test:** Synthetic marker and keyless/correct-key inspection of actual DB/journal/temp paths.

#### VC-STORE-02 — Final message write

- **Requirement:** F16.
- **Dependency:** VC-STORE-01, VC-SET-07.
- **Boundary:** native repository.
- **Done when:** Finalized authorized user/reply text persists transactionally with session/source IDs and expiry.
- **Focused test:** Restart store; committed turn survives; aborted/private turn creates no row.

#### VC-STORE-03 — Interrupted reply write

- **Requirement:** F16, A05.
- **Dependency:** VC-STORE-02, VC-VOICE-05.
- **Boundary:** native repository.
- **Done when:** Interrupted reply stores truthful interruption/progress status, not assumed complete hearing.
- **Focused test:** Mid-output fixture commits appropriate final/interrupted fields.

#### VC-STORE-04 — History read pagination

- **Requirement:** F16, S04.
- **Dependency:** VC-STORE-02.
- **Boundary:** native repository.
- **Done when:** Authorized bounded pages exclude expired/deleted/private data.
- **Focused test:** Seed >page-size; validate bounds, ordering and locked denial.

#### VC-STORE-05 — Retention filter

- **Requirement:** F16, S10, N10.
- **Dependency:** VC-STORE-02.
- **Boundary:** native query policy.
- **Done when:** 90day default and selected retention exclude expired records before any read/retrieval.
- **Focused test:** Controlled clock including backwards/forwards changes; expired sources never returned.

#### VC-STORE-06 — Retention physical cleanup

- **Requirement:** F16, S02, N10.
- **Dependency:** VC-STORE-05.
- **Boundary:** native maintenance.
- **Done when:** Eligible cleanup removes expired rows/dependencies within bounded maintenance transactions.
- **Focused test:** Restart/failure mid-cleanup preserves consistency; do not promise exact deletion time while OS stopped.

#### VC-STORE-07 — Storage quota accounting

- **Requirement:** F16, N10.
- **Dependency:** VC-STORE-01.
- **Boundary:** native quota service.
- **Done when:** 250MB accounting includes database/indexes/journals/inbox and reserved maintenance; excludes generic models.
- **Focused test:** Synthetic bounded files show exact account membership and warning at proposed80%.

#### VC-STORE-08 — History write reservation

- **Requirement:** F16, N10.
- **Dependency:** VC-STORE-07, VC-STORE-02.
- **Boundary:** native quota policy.
- **Done when:** No history-enabled turn starts without safe write reservation; full storage never silently switches privacy mode.
- **Focused test:** Near-cap/disk-full/write-failure fixtures preserve prior history and return actionable error.

#### VC-STORE-09 — Delete source transaction

- **Requirement:** F16, S10, A04.
- **Dependency:** VC-STORE-02.
- **Boundary:** native repository.
- **Done when:** Source deletion immediately removes app-visible message and invalidates dependent facts/index/cache.
- **Focused test:** Linked-source fixture and forced rollback verify atomic cascade and no stale recall.

#### VC-STORE-10 — Delete-all key reset

- **Requirement:** F16, S09, A09.
- **Dependency:** VC-STORE-09, VC-CTRL-04.
- **Boundary:** native reset.
- **Done when:** Authenticated delete-all cancels work, removes personal stores/inbox/keys and rejects stale reads/writes.
- **Focused test:** Reset race fixture; old ciphertext inaccessible; new storage requires fresh approved consent.

### INBOX — Locked ciphertext writes

#### VC-INBOX-01 — Vetted sealing composition review

- **Requirement:** F18, S09.
- **Dependency:** VC-KEY-01, VC-KEY-02.
- **Boundary:** security design task.
- **Done when:** Selected standard envelope-encryption APIs meet write-locked/read-authenticated policy without bespoke cryptography.
- **Focused test:** Review algorithm/version/AAD/key association/nonce/integrity threat model; unresolved composition blocks implementation.

#### VC-INBOX-02 — Public-key sealed write

- **Requirement:** F16, F18, S09.
- **Dependency:** VC-INBOX-01, VC-SET-07, VC-STORE-07.
- **Boundary:** native inbox.
- **Done when:** Locked authorized turn writes only bounded ciphertext and minimal metadata with private key unavailable.
- **Focused test:** Synthetic write inspects files; decryption/old history denied while locked; private mode zero writes.

#### VC-INBOX-03 — Authenticated inbox import

- **Requirement:** F16, S09.
- **Dependency:** VC-INBOX-02, VC-STORE-02.
- **Boundary:** native inbox.
- **Done when:** Unlocked authorized import verifies envelopes and atomically deduplicates records into SQLCipher.
- **Focused test:** Tamper/replay/crash-after-commit fixtures reject corruption and duplicate rows.

#### VC-INBOX-04 — Inbox expiry and reset

- **Requirement:** F16, S10, N10.
- **Dependency:** VC-INBOX-02, VC-STORE-05, VC-STORE-10.
- **Boundary:** native inbox maintenance.
- **Done when:** Expired envelopes are unreadable to retrieval/import and delete-all removes every pending envelope.
- **Focused test:** Clock/expired-import/reset race fixtures; quota releases after cleanup.

### MEM — Local facts and recall

#### VC-MEM-01 — Provenance-linked confirmed facts

- **Requirement:** F11, F16, S10.
- **Dependency:** VC-STORE-02.
- **Boundary:** native memory repository.
- **Done when:** Only eligible explicit/confirmed facts are stored with source links and status; no automatic emotional profile.
- **Focused test:** Unclear/private/interrupted/inferred statements cannot become confirmed facts.

#### VC-MEM-02 — Bounded lexical retrieval

- **Requirement:** F04, F11, S10.
- **Dependency:** VC-MEM-01, VC-STORE-05, VC-STORE-09.
- **Boundary:** native retrieval.
- **Done when:** Relevant eligible snippets are returned locally within budget; sources still exist and have not expired.
- **Focused test:** Synthetic cross-session facts plus expired/deleted/injection cases; empty recall is explicit.

#### VC-MEM-03 — Fact correction

- **Requirement:** F16, S10.
- **Dependency:** VC-MEM-01, VC-KEY-03.
- **Boundary:** native memory repository.
- **Done when:** Authenticated correction updates fact status/value and invalidates previous cached retrieval.
- **Focused test:** Correct synthetic preference; subsequent recall sees corrected value, old cache invalid.

#### VC-MEM-04 — Memory UI review

- **Requirement:** F16, S04.
- **Dependency:** VC-UX-14, VC-STORE-04, VC-MEM-01, VC-SET-06.
- **Boundary:** React Native screen.
- **Done when:** Authenticated paginated history/facts are reviewable and never persisted in JS storage.
- **Focused test:** UI auth-denial/pagination/lock-redaction tests; inspect JS persistence sinks.

#### VC-MEM-05 — Memory UI corrective actions

- **Requirement:** F16, A15.
- **Dependency:** VC-UX-14, VC-MEM-03, VC-MEM-04, VC-STORE-09, VC-STORE-10.
- **Boundary:** React Native screen.
- **Done when:** Explicit authenticated correction/delete actions expose clear results and storage cleanup choices.
- **Focused test:** UI action fixtures; cancelled/locked action changes nothing; successful action reflected.

#### VC-MEM-06 — Recall quality trial

- **Requirement:** F11, A04, A12.
- **Dependency:** VC-MEM-02, VC-MEM-03.
- **Boundary:** separate quality measurement.
- **Done when:** Frozen cross-session tests score appropriate recall and zero recall from deleted/expired/private sources.
- **Focused test:** Controlled dataset after restart/unlock; human rubric and forbidden-source pass/fail.

### LOCK — Lock transitions and privacy surfaces

#### VC-LOCK-01 — Generic lock transition

- **Requirement:** F18, A13, S04.
- **Dependency:** VC-CTRL-04, VC-KEY-04.
- **Boundary:** native policy.
- **Done when:** Lock cancels sensitive output and clears prior prompt/memory/context before generic standby.
- **Focused test:** Lock during retrieval/generation/playback; old private markers never reach sink.

#### VC-LOCK-02 — Locked memory/privilege denial

- **Requirement:** F18, A15, S07.
- **Dependency:** VC-LOCK-01, VC-KEY-03.
- **Boundary:** native access policy.
- **Done when:** Wake/model/voice requests while locked cannot read/delete history or change privacy controls.
- **Focused test:** Bystander-command fixture always requires authenticated screen flow.

#### VC-LOCK-03 — Authenticated unlock re-entry

- **Requirement:** F18.
- **Dependency:** VC-LOCK-01, VC-KEY-03.
- **Boundary:** native policy.
- **Done when:** Unlock alone does not reopen history; explicit authentication restores memory session.
- **Focused test:** Unlock then recall request sees generic mode until authentication passes.

#### VC-LOCK-04 — Private UI snapshot protection

- **Requirement:** S04.
- **Dependency:** VC-UX-14, VC-MEM-04, VC-LOCK-01.
- **Boundary:** platform UI privacy.
- **Done when:** History UI is redacted on lock/app switch; notifications contain no conversation text.
- **Focused test:** Physical app-switcher/lock notification inspection on each platform; document screenshot limits.

#### VC-LOCK-05 — Android backup/transfer exclusions

- **Requirement:** F19, S02, A09.
- **Dependency:** VC-STORE-01, VC-INBOX-02, VC-KEY-02.
- **Boundary:** Android packaging.
- **Done when:** Personal DB/inbox/journals/keys are excluded from cloud backup and device transfer.
- **Focused test:** Actual supported backup/restore/transfer inspection; no recoverable synthetic history or automatic listening.

#### VC-LOCK-06 — iOS backup/transfer exclusions

- **Requirement:** F19, S02, A09.
- **Dependency:** VC-STORE-01, VC-INBOX-02, VC-KEY-01.
- **Boundary:** iOS packaging.
- **Done when:** Personal DB/inbox/journals/keys are device-only and excluded from cloud backup/transfer.
- **Focused test:** Actual supported backup/restore/transfer inspection; no recoverable synthetic history or automatic listening.

#### VC-LOCK-07 — Content-free diagnostics

- **Requirement:** S02, S03.
- **Dependency:** VC-BASE-03.
- **Boundary:** native diagnostics.
- **Done when:** Only bounded volatile state/error/resource codes exist; no transcript/prompt/keys or uploaded logs.
- **Focused test:** Synthetic markers across errors/crash paths and sinks; no content or persistent behavioral trail.

### BEHAV — Conversation behaviour

#### VC-BEHAV-01 — AI identity and supportive persona

- **Requirement:** F06, F07.
- **Dependency:** VC-LLM-02.
- **Boundary:** persona policy.
- **Done when:** Brief warm responses identify AI honestly and acknowledge expressed feelings without diagnosis/exclusivity pressure.
- **Focused test:** Human-reviewed synthetic emotion/identity cases against frozen rubric.

#### VC-BEHAV-02 — Uncertainty and capability boundaries

- **Requirement:** F06, F14, F15.
- **Dependency:** VC-BEHAV-01.
- **Boundary:** response policy.
- **Done when:** No claim of live browsing, phone actions, professional diagnosis or emergency action; no extra permissions.
- **Focused test:** Current-news/call/photo/diagnosis fixtures acknowledge limits; action spies remain unused.

#### VC-BEHAV-03 — Imminent-danger response policy

- **Requirement:** F07.
- **Dependency:** VC-BEHAV-01.
- **Boundary:** response policy.
- **Done when:** Explicit danger receives agreed supportive guidance to contact local emergency/trusted help without collecting location or claiming monitoring.
- **Focused test:** Human-approved synthetic scenarios; exact wording rubric review before public release.

#### VC-BEHAV-04 — Pre-speech clause policy

- **Requirement:** F06, S10.
- **Dependency:** VC-BEHAV-01, VC-BEHAV-02, VC-BEHAV-03, VC-VOICE-04.
- **Boundary:** native output policy.
- **Done when:** Each generated clause passes configured policy before audible output; cancellation epoch checked again.
- **Focused test:** Unsafe/stale synthetic clause never reaches playback sink; record limits of small-model policy.

#### VC-BEHAV-05 — Multi-turn quality trial

- **Requirement:** N05, A12.
- **Dependency:** VC-BEHAV-04, VC-MEM-02.
- **Boundary:** human evaluation.
- **Done when:** 100 frozen synthetic conversations score relevance/continuity/clarity/tone;≥90% acceptable target, safety/privacy independent.
- **Focused test:** Human rubric results with sample counts; failures become narrow fix tasks.

### JOIN — Small vertical integrations

#### VC-JOIN-01 — One offline generic spoken turn

- **Requirement:** F05, F06, F13, A07.
- **Dependency:** VC-TURN-05, VC-LLM-03, VC-VOICE-04, VC-BEHAV-04.
- **Boundary:** integration seam.
- **Done when:** Activated input yields a spoken local reply using real adapters, with no persistent history.
- **Focused test:** Synthetic wake/question→reply in airplane mode; trace stage errors and egress.

#### VC-JOIN-02 — Spoken follow-up session

- **Requirement:** F04, A03.
- **Dependency:** VC-JOIN-01, VC-TURN-03, VC-CTRL-05.
- **Boundary:** integration seam.
- **Done when:** Follow-up within active session needs no wake; idle/end closes context.
- **Focused test:** Two-turn synthetic dialogue plus timeout and combined wake-question.

#### VC-JOIN-03 — Interrupt-and-replace turn

- **Requirement:** F09, F10, A05.
- **Dependency:** VC-JOIN-01, VC-TURN-07, VC-TURN-08.
- **Boundary:** integration seam.
- **Done when:** User interruption stops old speech and handles exactly one new request.
- **Focused test:** End-to-end synthetic interruption; no self-trigger, stale audio or duplicate turn.

#### VC-JOIN-04 — Unlocked history integration

- **Requirement:** F16, A04.
- **Dependency:** VC-JOIN-02, VC-STORE-03, VC-MEM-02, VC-KEY-03.
- **Boundary:** integration seam.
- **Done when:** Consented authenticated turns persist and eligible facts can be recalled after restart.
- **Focused test:** Synthetic save/restart/auth/recall; private and deleted sources cannot reappear.

#### VC-JOIN-05 — Locked generic/inbox integration

- **Requirement:** F18, A13, A15.
- **Dependency:** VC-JOIN-01, VC-INBOX-03, VC-INBOX-04, VC-LOCK-01, VC-LOCK-02, VC-LOCK-03.
- **Boundary:** integration seam.
- **Done when:** Locked dialogue uses no old personal memory; new history is sealed and imported only after authentication.
- **Focused test:** Lock mid-private turn then generic turn/import; inspect output/storage/races.

### VERIFY — Development validation and release gates

#### VC-VERIFY-01 — Freeze device/workload matrix

- **Requirement:** A12, N01, N02, N03, N04, N05, N06, N07, N08.
- **Dependency:** No task prerequisite; relevant environment access and task authorization still required.
- **Boundary:** test planning.
- **Done when:** Declare OS/devices/routes/datasets/sample counts and scoring before measuring targets.
- **Focused test:** Review reproducible workload definitions; untested hardware stays untested.

#### VC-VERIFY-02 — Meaningful-audio latency trial

- **Requirement:** N01, A12.
- **Dependency:** VC-VERIFY-01, VC-JOIN-01.
- **Boundary:** physical-device measurement.
- **Done when:** Report cold/warm complete latency including endpoint; median≤1.5s/p95≤3s target.
- **Focused test:** Annotated end-of-user-speech→meaningful audio on each route/configuration; filler excluded.

#### VC-VERIFY-03 — Interruption latency trial

- **Requirement:** N02, A05, A12.
- **Dependency:** VC-VERIFY-01, VC-JOIN-03.
- **Boundary:** physical-device measurement.
- **Done when:** Report p95 intelligible-user-onset→old-playback-stop;≤300ms target.
- **Focused test:** Repeated annotated interruptions; report misses/noise and distributions.

#### VC-VERIFY-04 — Foreground60min active trial

- **Requirement:** N06, N08, A12.
- **Dependency:** VC-VERIFY-01, VC-JOIN-02.
- **Boundary:** physical-device measurement.
- **Done when:** No crash/thermal shutdown; final15min latency meets targets; battery/RSS reported.
- **Focused test:** 60min frozen scripted foreground workload per device; baseline battery/temperature captured.

#### VC-VERIFY-05 — Screen-off60min active trial

- **Requirement:** N06, N08, A13.
- **Dependency:** VC-VERIFY-01, VC-JOIN-05, VC-AUDIO-09, VC-AUDIO-10.
- **Boundary:** physical-device measurement.
- **Done when:** Same active targets in permitted screen-off CPU mode; no private-memory leakage.
- **Focused test:** 60min scripted screen-off workload per device; failures/OS restrictions explicit.

#### VC-VERIFY-06 — Screen-off8h standby trial

- **Requirement:** N03, N07, N08, A13, A14.
- **Dependency:** VC-VERIFY-01, VC-TURN-02, VC-AUDIO-09, VC-AUDIO-10.
- **Boundary:** physical-device measurement.
- **Done when:** Report wake availability/false activations/battery and honest termination state over8h.
- **Focused test:** Frozen ambient/wake schedule; per-device aggregate evidence; no all-day claim.

#### VC-VERIFY-07 — Offline network/privacy audit

- **Requirement:** S01, S07, S08, A07, A10, A16.
- **Dependency:** VC-JOIN-04, VC-JOIN-05, VC-PACK-05.
- **Boundary:** full-app privacy gate.
- **Done when:** No conversation/history/personal-model traffic or training endpoints; identity-only provider/relay traffic explicitly isolated; offline conversation works.
- **Focused test:** Capture all app-process traffic with synthetic markers; inspect SDKs/manifests/endpoint paths.

#### VC-VERIFY-08 — Persistence/backup privacy audit

- **Requirement:** S02, S03, S04, S08, S09, A08, A09.
- **Dependency:** VC-JOIN-05, VC-LOCK-04, VC-LOCK-05, VC-LOCK-06, VC-LOCK-07.
- **Boundary:** full-app privacy gate.
- **Done when:** Only declared encrypted personal stores persist; no prohibited copies/content diagnostics.
- **Focused test:** Inspect files/journals/temp/logs/snapshots/backups; verify encryption rather than text-search alone.

#### VC-VERIFY-09 — Resource-failure safety trial

- **Requirement:** F12, F14, N08.
- **Dependency:** VC-JOIN-04, VC-STORE-08.
- **Boundary:** failure validation.
- **Done when:** Memory pressure/low battery/thermal/disk errors pause safely, preserving committed ciphertext and no fallback.
- **Focused test:** Injected failures plus physical resource events; no plaintext spill or silent history loss.

#### VC-VERIFY-10 — Requirement evidence closure

- **Requirement:** F01, F02, F03, F04, F05, F06, F07, F08, F09, F10, F11, F12, F13, F14, F15, F16, F17, F18, F19, S01, S02, S03, S04, S05, S06, S07, S08, S09, S10, A01, A02, A03, A04, A05, A06, A07, A08, A09, A10, A11, A12, A13, A14, A15, A16.
- **Dependency:** VC-VERIFY-07, VC-VERIFY-08.
- **Boundary:** release review gate.
- **Done when:** Every requirement has evidence or explicit blocked/not-tested result; privacy failure blocks release.
- **Focused test:** Traceability audit; task approval cannot substitute for full-app acceptance evidence.

#### VC-VERIFY-11 — Release package preparation

- **Requirement:** S05, S06, S08.
- **Dependency:** VC-VERIFY-10, VC-PACK-10.
- **Boundary:** release documentation only.
- **Done when:** Prepare supported-device list, license inventory, signing provenance, privacy disclosures and rollback/pilot plan.
- **Focused test:** Review concrete package; deployment/store submission requires separate authorization.

### GATE — Feasibility review before persistent memory

#### VC-GATE-01 — Generic foreground60min feasibility

- **Requirement:** N06, N08, A12.
- **Dependency:** VC-VERIFY-01, VC-JOIN-02.
- **Boundary:** physical feasibility experiment.
- **Done when:** Record sustained foreground generic voice workload before persistent memory is introduced.
- **Focused test:** 60min synthetic generic workload; final15min latency, battery, RSS and heat; target failures explicit.

#### VC-GATE-02 — Generic screen-off60min feasibility

- **Requirement:** N06, N08, A13.
- **Dependency:** VC-VERIFY-01, VC-JOIN-02, VC-AUDIO-09, VC-AUDIO-10.
- **Boundary:** physical feasibility experiment.
- **Done when:** Record platform-compliant CPU generic dialogue with screen off before persistent memory.
- **Focused test:** 60min synthetic screen-off workload on each proposed platform; no laptop/simulator pass.

#### VC-GATE-03 — Generic standby8h feasibility

- **Requirement:** N03, N07, N08, A13, A14.
- **Dependency:** VC-VERIFY-01, VC-TURN-02, VC-AUDIO-09, VC-AUDIO-10.
- **Boundary:** physical feasibility experiment.
- **Done when:** Record8h permitted standby availability/battery/false triggers before persistent memory.
- **Focused test:** Frozen ambient/wake schedule on proposed physical phones; terminated capture reported honestly.

#### VC-GATE-04 — Generic companion feasibility decision

- **Requirement:** F17, A12, A13, N01, N02, N03, N04, N05, N06, N07, N08.
- **Dependency:** VC-GATE-01, VC-GATE-02, VC-GATE-03, VC-VERIFY-02, VC-VERIFY-03, VC-TURN-09, VC-TURN-10, VC-LLM-06, VC-VOICE-06.
- **Boundary:** human decision gate.
- **Done when:** Human reviews per-platform pass/fail/not-tested evidence and accepts feasible scope or separately reviews changes before persistent memory implementation.
- **Focused test:** Decision report references actual experiments; untested or failed configurations cannot silently become supported.

## Requirement traceability

The following lists primary implementation/validation owners, excluding the all-requirements closure audit for readability. Passing a unit test alone does not close a full-app acceptance criterion.

| Requirement | Source requirement | Task owners |
|---|---|---|
| F01 | No microphone capture occurs before permission and a user-initiated Start action. Permission denial leaves the app usable for settings/help, without repeated prompts. | VC-UX-03, VC-UX-04, VC-UX-11, VC-SET-04, VC-SET-05, VC-AUDIO-01, VC-AUDIO-05 |
| F02 | The app distinguishes setup, permission required, stopped, standby, listening, thinking, speaking, paused, and error states. Required system indicators/notification controls remain available outside the UI. | VC-UX-02, VC-UX-05, VC-UX-09, VC-UX-11, VC-UX-14, VC-BASE-03, VC-CTRL-01, VC-SET-06, VC-AUDIO-02 |
| F03 | In standby, only local activation detection and its minimal bounded audio buffer operate. Ordinary ambient speech must not enter conversational inference before activation. | VC-TURN-01, VC-TURN-02 |
| F04 | Activation opens a session; follow-ups use bounded session context and relevant permitted local memories. Saved history is not automatically loaded in full into every prompt. | VC-UX-03, VC-CTRL-05, VC-CTRL-06, VC-TURN-03, VC-LLM-03, VC-MEM-02, VC-JOIN-02 |
| F05 | Speech input and replies require no typing. Visible controls remain available for Start, Stop, retry, volume, and accessibility. | VC-UX-01, VC-UX-05, VC-UX-07, VC-UX-09, VC-UX-10, VC-UX-11, VC-UX-12, VC-UX-13, VC-UX-14, VC-SET-06, VC-SET-08, VC-TURN-05, VC-LLM-05, VC-VOICE-02, VC-VOICE-03, VC-VOICE-04, VC-VOICE-06, VC-JOIN-01 |
| F06 | Replies address the latest utterance, session context, and eligible local memory. Treat recalled text as information, not privileged instructions. Typical replies are brief. | VC-LLM-01, VC-LLM-02, VC-LLM-04, VC-BEHAV-01, VC-BEHAV-02, VC-BEHAV-04, VC-JOIN-01 |
| F07 | The companion responds supportively to expressed feelings without claiming to diagnose emotions or reliably infer a person’s mental state from their voice. | VC-UX-02, VC-UX-08, VC-BEHAV-01, VC-BEHAV-03 |
| F08 | Low-confidence or unclear input results in a brief clarification request, rather than an invented interpretation. | VC-UX-02, VC-UX-08, VC-TURN-04, VC-TURN-05, VC-TURN-06 |
| F09 | Confirmed new user speech during playback stops the old reply and cancels its queued audio. The app then handles the new turn. Noise alone should not routinely interrupt playback. | VC-UX-02, VC-UX-05, VC-CTRL-03, VC-TURN-08, VC-VOICE-04, VC-JOIN-03 |
| F10 | The app must not transcribe, respond to, or wake itself from its own speech playback. | VC-UX-02, VC-TURN-07, VC-JOIN-03 |
| F11 | Working context is bounded; relevant history may be retrieved locally. The app must distinguish remembered information from uncertain inference and must not fabricate recall. | VC-LLM-03, VC-MEM-01, VC-MEM-02, VC-MEM-06 |
| F12 | Stop takes effect locally, without a network request. Privacy lifecycle rules apply during permission revocation, calls, microphone contention, errors, and app transitions. | VC-UX-02, VC-UX-05, VC-CTRL-01, VC-CTRL-02, VC-CTRL-05, VC-CTRL-06, VC-CTRL-07, VC-AUDIO-02, VC-AUDIO-04, VC-AUDIO-07, VC-AUDIO-08, VC-VERIFY-09 |
| F13 | Once setup is complete, an offline guest conversation works with Wi-Fi and mobile data disabled. No account or authentication-server connectivity is required. | VC-UX-01, VC-UX-04, VC-BASE-01, VC-BASE-02, VC-BASE-04, VC-SET-01, VC-LLM-01, VC-JOIN-01 |
| F14 | Unsupported devices or missing models receive a clear explanation. The app never silently switches to cloud processing. | VC-UX-04, VC-UX-07, VC-UX-08, VC-PACK-07, VC-PACK-08, VC-PACK-09, VC-VOICE-01, VC-BEHAV-02, VC-VERIFY-09 |
| F15 | No unsolicited companion speech outside an activated interaction or automatic microphone restart after reboot/crash. An operational background-service notification is permitted and may be required. | VC-UX-02, VC-UX-05, VC-CTRL-02, VC-CTRL-08, VC-BEHAV-02 |
| F16 | Persist text history and derived memory locally with encryption; allow review, correction, delete-one, delete-all, and history-disabled private sessions. | VC-UX-01, VC-UX-03, VC-UX-04, VC-UX-06, VC-UX-07, VC-UX-08, VC-UX-11, VC-UX-12, VC-UX-13, VC-UX-14, VC-SET-02, VC-SET-07, VC-VOICE-05, VC-STORE-01, VC-STORE-02, VC-STORE-03, VC-STORE-04, VC-STORE-05, VC-STORE-06, VC-STORE-07, VC-STORE-08, VC-STORE-09, VC-STORE-10, VC-INBOX-02, VC-INBOX-03, VC-INBOX-04, VC-MEM-01, VC-MEM-03, VC-MEM-04, VC-MEM-05, VC-JOIN-04 |
| F17 | Background and screen-off conversation is supported only through permitted platform behaviour and explicit opt-in; loss of availability is shown honestly. | VC-UX-01, VC-UX-03, VC-UX-04, VC-UX-07, VC-UX-08, VC-UX-10, VC-UX-12, VC-UX-13, VC-UX-14, VC-SET-03, VC-AUDIO-01, VC-AUDIO-03, VC-AUDIO-05, VC-AUDIO-06, VC-AUDIO-09, VC-AUDIO-10, VC-GATE-04 |
| F18 | Locked-screen operation cannot reveal stored personal memory or change privacy controls without authentication. | VC-UX-03, VC-UX-06, VC-UX-07, VC-UX-08, VC-UX-11, VC-UX-12, VC-UX-13, VC-UX-14, VC-KEY-01, VC-KEY-02, VC-KEY-03, VC-KEY-04, VC-INBOX-01, VC-INBOX-02, VC-LOCK-01, VC-LOCK-02, VC-LOCK-03, VC-JOIN-05 |
| F19 | Exclude local history, memory indexes, keys, and future personalized model state from app-managed cloud sync, OS cloud backups, and device transfer. | VC-LOCK-05, VC-LOCK-06 |
| S01 | No conversation content leaves the device through any component, including speech APIs, model runtimes, SDKs, telemetry, support uploads, and crash reporting. System speech/voice components are permitted only if their offline behaviour is verified. | VC-BASE-04, VC-PACK-05, VC-PACK-10, VC-TURN-05, VC-LLM-01, VC-VOICE-01, VC-VOICE-02, VC-VOICE-03, VC-VERIFY-07 |
| S02 | Conversation data persists only in the declared encrypted local history/memory store and necessary encrypted storage journals. No plaintext temporary files, logs, notification previews, diagnostics, cloud backups, or device-transfer copies. | VC-CTRL-04, VC-TURN-01, VC-STORE-01, VC-STORE-06, VC-LOCK-05, VC-LOCK-06, VC-LOCK-07, VC-VERIFY-08 |
| S03 | Logging is disabled for conversational input/output in development and production. Later tests use synthetic conversations and must not record real-user content. | VC-LOCK-07, VC-VERIFY-08 |
| S04 | No conversation content in app-switcher snapshots or lock-screen notifications. History screens require an unlocked/authenticated device; optional live captions are local and hidden at lock. | VC-UX-06, VC-UX-08, VC-UX-10, VC-UX-14, VC-BASE-03, VC-CTRL-03, VC-CTRL-04, VC-STORE-04, VC-MEM-04, VC-LOCK-01, VC-LOCK-04, VC-VERIFY-08 |
| S05 | Downloaded models are integrity-checked against trusted release metadata. Model/voice licenses and dependencies must be reviewed before inclusion. | VC-PACK-01, VC-PACK-02, VC-PACK-03, VC-PACK-04, VC-PACK-06, VC-PACK-07, VC-PACK-08, VC-VERIFY-11 |
| S06 | Model downloads use authenticated encrypted transport and integrity verification. Local encryption credentials use platform secure storage. No service secrets are embedded in the app. | VC-PACK-03, VC-PACK-04, VC-PACK-05, VC-PACK-06, VC-PACK-10, VC-KEY-01, VC-KEY-02, VC-VERIFY-11 |
| S07 | There are no conversation upload endpoints or remote user/conversation database. Account service is stateful and isolated from conversation. Access to local memory and privileged privacy actions requires the specified device authentication. | VC-UX-04, VC-SET-01, VC-SET-02, VC-PACK-05, VC-KEY-03, VC-LOCK-02, VC-VERIFY-07 |
| S08 | Unauthorized persistence or any MVP conversation/memory transmission blocks release regardless of quality or speed. | VC-PACK-10, VC-VERIFY-07, VC-VERIFY-08, VC-VERIFY-11 |
| S09 | History, derived memory, and future personal adapters are encrypted at rest with platform-protected keys and authenticated integrity protection. Review key accessibility while locked. | VC-KEY-01, VC-KEY-02, VC-KEY-04, VC-STORE-01, VC-STORE-10, VC-INBOX-01, VC-INBOX-02, VC-INBOX-03, VC-VERIFY-08 |
| S10 | Deleting source data must invalidate derived memory. Stored conversations never override system privacy/safety rules. | VC-UX-06, VC-CTRL-04, VC-LLM-04, VC-STORE-05, VC-STORE-09, VC-INBOX-04, VC-MEM-01, VC-MEM-02, VC-MEM-03, VC-BEHAV-04 |
| A01 | Fresh install: inspect capture state before Start and before permission; no audio capture occurs. Permission denial leaves capture stopped. | VC-UX-03, VC-SET-04, VC-SET-05 |
| A02 | Granted permission: ordinary speech during standby produces no conversational response; the configured wake phrase activates a session with a visible/audible cue. Evaluate false activation separately. | VC-TURN-02 |
| A03 | Wake phrase plus question in one sentence receives a relevant answer without repeating the question. | VC-TURN-03, VC-JOIN-02 |
| A04 | With history enabled, a synthetic fact survives Stop/restart and is recalled appropriately after unlock. Delete the source and dependent memory; the fact no longer appears through retrieval. Private-session facts never persist. | VC-UX-03, VC-SET-07, VC-STORE-09, VC-MEM-06, VC-JOIN-04 |
| A05 | User interrupts spoken output; old audio and queued output stop within the target and the new request is handled. Playback does not trigger recognition of itself. | VC-CTRL-03, VC-TURN-07, VC-TURN-08, VC-VOICE-05, VC-STORE-03, VC-JOIN-03, VC-VERIFY-03 |
| A06 | Stop releases capture; active-session timeout returns to standby. Enabled background mode continues on UI exit/lock where permitted. Calls, revocation, termination, and failures obey the revised lifecycle policy without deleting committed history. | VC-UX-03, VC-CTRL-02, VC-CTRL-05, VC-SET-03, VC-AUDIO-03, VC-AUDIO-04, VC-AUDIO-06, VC-AUDIO-07 |
| A07 | With setup complete and all networking blocked, guest conversations still work. Online packet inspection across all app processes shows no conversation-dependent requests or content egress. | VC-JOIN-01, VC-VERIFY-07 |
| A08 | Synthetic markers appear only in the encrypted local store and authorized in-memory processing. Inspect files, journals, logs, diagnostics, backups and transfer/restore results for prohibited plaintext/copies. Test encryption and backup exclusions; a clean text search alone is insufficient. | VC-VERIFY-08 |
| A09 | Restart on the same phone preserves authorized local history; cloud backup/device transfer never restores it or its keys. Local deletion/reset and private-mode behaviour meet the specified policy. | VC-STORE-10, VC-LOCK-05, VC-LOCK-06, VC-VERIFY-08 |
| A10 | Guest setup and normal use require no sign-up/login. Optional sign-in has identity-only provider/relay traffic and minimal identity directory in Neon or conversation endpoints. Device authentication still protects local history. | VC-BASE-01, VC-BASE-02, VC-SET-01, VC-VERIFY-07 |
| A11 | Headphone disconnection does not unexpectedly play private replies through the speaker. Missing models and unsupported devices never trigger cloud fallback. | VC-UX-07, VC-PACK-09, VC-AUDIO-08, VC-VOICE-01 |
| A12 | Run agreed performance, activation, quality, memory-recall, background, and 60-minute tests on each supported configuration; report distributions and failures. | VC-TURN-09, VC-TURN-10, VC-LLM-06, VC-VOICE-06, VC-MEM-06, VC-BEHAV-05, VC-VERIFY-01, VC-VERIFY-02, VC-VERIFY-03, VC-VERIFY-04, VC-GATE-01, VC-GATE-04 |
| A13 | Start mode while visible, leave UI, lock screen, and speak the wake phrase: generic conversation works on supported devices without reopening UI. Repeat under declared idle/battery conditions; no private memories are revealed while locked. | VC-UX-03, VC-AUDIO-09, VC-AUDIO-10, VC-LOCK-01, VC-JOIN-05, VC-VERIFY-05, VC-VERIFY-06, VC-GATE-02, VC-GATE-03, VC-GATE-04 |
| A14 | Force-stop, reboot, kill the service, and remove permission: no claim that wake listening remains available. Restart requires a permitted user action. | VC-CTRL-08, VC-AUDIO-09, VC-AUDIO-10, VC-VERIFY-06, VC-GATE-03 |
| A15 | Notification/voice Stop works without opening the app. Requests to read history, delete it, or change privacy settings while locked require unlock/authentication. | VC-UX-03, VC-CTRL-07, VC-AUDIO-02, VC-MEM-05, VC-LOCK-02, VC-JOIN-05 |
| A16 | Training and all model-update upload paths are absent/disabled in MVP; network inspection confirms no history or personal model state leaves the phone. | VC-VERIFY-07 |
| N01 | Meaningful reply audio: median ≤1.5s and p95 ≤3s, measured from annotated end of speech, including endpoint detection; filler excluded. | VC-VERIFY-01, VC-VERIFY-02, VC-GATE-04 |
| N02 | Interruption stops playback p95 ≤300ms from intelligible speech onset. | VC-TURN-08, VC-VERIFY-01, VC-VERIFY-03, VC-GATE-04 |
| N03 | Wake detection ≥95% in frozen quiet set; ≤1 false activation per 8h agreed ambient set. | VC-TURN-09, VC-VERIFY-01, VC-VERIFY-06, VC-GATE-03, VC-GATE-04 |
| N04 | ASR WER ≤10% agreed English set; report accents/names/numbers/noise separately. | VC-TURN-10, VC-VERIFY-01, VC-GATE-04 |
| N05 | Human conversation rubric ≥90% acceptable across 100 frozen multi-turn conversations; safety/privacy separate gates. | VC-LLM-06, VC-BEHAV-05, VC-VERIFY-01, VC-GATE-04 |
| N06 | 60min foreground and screen-off active trials: no crash/thermal shutdown; final15min latency meets targets. | VC-VERIFY-01, VC-VERIFY-04, VC-VERIFY-05, VC-GATE-01, VC-GATE-02, VC-GATE-04 |
| N07 | 8h screen-off standby: availability, false activation, battery and honest stopped-state evidence. | VC-VERIFY-01, VC-VERIFY-06, VC-GATE-03, VC-GATE-04 |
| N08 | Approved planning budgets: standby ≤2 battery percentage points/h; active ≤15 points/h; app peak RSS <2.5GB; generic model pack <2GB. | VC-LLM-06, VC-VERIFY-01, VC-VERIFY-04, VC-VERIFY-05, VC-VERIFY-06, VC-VERIFY-09, VC-GATE-01, VC-GATE-02, VC-GATE-03, VC-GATE-04 |
| N09 | Bounded working context 4096 tokens, retrieved memory ≤512 tokens, normal reply ≤256 generated tokens; continuation bounded. | VC-LLM-03, VC-LLM-05 |
| N10 | Personal store ≤250,000,000 bytes incl inbox/journals/indexes; 90day default retention; proposed warning at80%; no silent mode switch/deletion outside selected policy. | VC-UX-07, VC-STORE-05, VC-STORE-06, VC-STORE-07, VC-STORE-08, VC-INBOX-04 |

## Tracking and change management

The JSON backlog is the canonical task/requirement/dependency record. The CSV is an editable operational view keyed by stable task ID; reconcile tracker changes into the JSON at each review. Store multiple test runs in the task evidence list, not by overwriting the previous result.

Task workflow: `planned → ready → in_progress → awaiting_review → approved`. Use `blocked` with reason and unblocking task; use `deferred` only with recorded scope decision. Keep implementation status (`not_started/in_progress/implemented`) separate from verification (`not_run/pass/fail/not_tested_on_required_device`) and human approval. An implemented task with missing required evidence remains blocked or awaiting evidence; never label it approved automatically.

Each evidence record should include test ID, command/procedure, fixture/version, model revision, environment/device/OS/route, result, timestamp, artifact link, and limitation. Record synthetic aggregate measurements without real conversation content.

For a scope change, identify affected requirement/task IDs, change only necessary acceptance criteria, revise dependencies, and ask for review of the actual change. Never reuse a retired task ID. Freeze the device/workload matrix before benchmark results.

## Suggested initial review slices

1. Foundation/contracts: BASE-03 → BASE-04 → CTRL-01, plus Android/iOS shell tasks when build environments are available. These can use synthetic adapters without converting models.
2. User control: permission gates, Start/Stop, consent and safe restart. Stop/cancellation precede live voice integration.
3. Platform audio feasibility and protected-key probes early; independent Android/iOS tasks expose blockers separately.
4. Model preparation/readiness, activation, ASR, CPU reply and offline voice adapters. A real turn is integrated only after its boundaries pass.
5. Encrypted storage/inbox/recall, then small memory and lock integrations. UI work uses controlled fake interfaces until secure native contracts are ready.
6. Physical quality/performance/privacy gates, followed by release preparation. Product support/feasibility is decided from evidence, not parameter counts.

The suggested slices are planning guidance, not automatic permission. Any task lacking SDK/device/access is marked blocked. Privacy requirements are designed and tested as features are built; full-app audits remain mandatory before release.

## Non-goals kept out of the backlog

Optional social identity is in scope per the amendment. Deferred: cloud inference/history/sync, calls/camera/contacts/location/other-app control, browsing, analytics/ads, voiceprints, emotional diagnosis, voice cloning, local training, personalized model upload, federation or deployment execution. Future training needs separate requirements and privacy approval. There are no new permissions or hidden feature flags enabling these paths.

## Task completion report template

```text
Task ID / outcome:
Scope and changed files / commit:
Requirements covered:
Focused tests and regression checks:
Environment/device/model revision:
Result: pass / fail / blocked / not run
Evidence links:
Privacy and known limitations:
Implementation / verification / approval status:
Next proposed task (not started):
```




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

## Revised authentication tasks

| ID | Responsibility | Dependencies |
|---|---|---|
| VC-AUTH-01 | Neon/native auth feasibility and provider configuration | VC-UX-14 |
| VC-AUTH-02 | Optional identity screen | VC-AUTH-01 |
| VC-AUTH-03 | Apple native identity adapter | VC-AUTH-01 |
| VC-AUTH-04 | Google native identity adapter | VC-AUTH-01 |
| VC-AUTH-05 | Better Auth account service | VC-AUTH-01 |
| VC-AUTH-06 | Secure identity credential storage | VC-AUTH-03, VC-AUTH-04, VC-AUTH-05 |
| VC-AUTH-07 | Offline expiry and revocation state | VC-AUTH-06 |
| VC-AUTH-08 | Authenticated sign-out | VC-AUTH-06 |
| VC-AUTH-09 | Identity switch and reset | VC-AUTH-08 |
| VC-AUTH-10 | Remote account deletion and provider revocation | VC-AUTH-06, VC-AUTH-05 |
| VC-AUTH-11 | Identity privacy and store disclosures | VC-AUTH-02, VC-AUTH-10 |
| VC-AUTH-12 | Provider integration verification | VC-AUTH-03, VC-AUTH-04, VC-AUTH-05, VC-AUTH-07, VC-AUTH-08, VC-AUTH-09, VC-AUTH-10, VC-AUTH-11, VC-AUTH-14, VC-AUTH-15, VC-AUTH-16, VC-AUTH-17 |
| VC-AUTH-13 | Neon identity schema/migrations | VC-AUTH-01, VC-AUTH-05 |
| VC-AUTH-14 | Account API authorization | VC-AUTH-13 |
| VC-AUTH-15 | Email sign-up verification and recovery | VC-AUTH-05, VC-AUTH-13 |
| VC-AUTH-16 | Account retention deletion and restore | VC-AUTH-10, VC-AUTH-13 |
| VC-AUTH-17 | Provider/privacy release assessment | VC-AUTH-13, VC-AUTH-16 |

## Merged visual and delivery scope — 5 October 2026

### VC-VIS-01 — Controller driven ripple states

- Requirements: VR01
- Depends on: VC-CTRL-01
- Scope: Bind animation to native state only.
- Acceptance: Rounded blue/lavender ripples animate only during listening and speaking; stopped, standby and thinking remain distinct and truthful.
- Focused test: Inject all controller states; stopped never resembles active capture.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-VIS-02 — Accessible motion and theme tokens

- Requirements: VR02
- Depends on: VC-VIS-01
- Scope: Implement shared theme and reduced motion.
- Acceptance: One-second loop is the requested preview and initial adjustable design parameter; reduced motion freezes decoration; light/dark text and controls meet defined contrast and platform scaling targets.
- Focused test: Test reduced motion, maximum text scaling and measured semantic contrast; do not reuse old teal results.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-VIS-03 — Spoken response text fallback

- Requirements: VR03
- Depends on: VC-CTRL-01
- Scope: Display only assistant output released to speech.
- Acceptance: Without rich content, spoken clauses appear progressively in the foreground; unspoken cancelled output is excluded and interruption is labelled.
- Focused test: Use interrupted and superseded clauses; ensure hidden draft tokens never display.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-VIS-04 — Independent display preferences

- Requirements: VR04
- Depends on: VC-SET-07
- Scope: Persist non-content local display preferences.
- Acceptance: Text defaults on, images/video off; Voice only disables all visuals while retaining previous individual choices; voice changes apply only in an active authorized session.
- Focused test: Test all combinations, restore from Voice only, restart and locked preference-change denial.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-VIS-05 — Result card selection and sources

- Requirements: VR05
- Depends on: VC-VIS-03, VC-VIS-04
- Scope: Render safe bounded result cards.
- Acceptance: Allowed rich results replace the default text card, with recoverable spoken answer, source attribution and explicit media availability; no invented ratings, travel time or current facts.
- Focused test: Fixture missing sources/media and unavailable tabs; no fabricated values.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-VIS-06 — Visual inactivity controller

- Requirements: VR06
- Depends on: VC-VIS-05
- Scope: Own visual expiry independent of audio.
- Acceptance: Dismiss after 20 seconds with no speech, processing, loading, interaction, accessibility focus or video playback; each relevant event resets timer; dismissal never stops listening.
- Focused test: Fake-clock boundaries at 19.9 and20 seconds, touch/scroll/focus/loading and live speech cases.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-VIS-07 — Pin dismiss and stale result cancellation

- Requirements: VR07
- Depends on: VC-VIS-06
- Scope: Control result lifetime.
- Acceptance: Keep visible pins only the current session/card; dismiss remains available; a new query, Stop, lock or privacy epoch clears old content and stale callbacks cannot reopen it.
- Focused test: Pin then lock/Stop/new-query; inject old result callback and verify no resurfacing.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-VIS-08 — User initiated media playback

- Requirements: VR08
- Depends on: VC-VIS-05
- Scope: Load images/videos only when permitted.
- Acceptance: No video autoplay; playback begins by tap; Eilo pauses speech and listening during video, clearly exposes Resume conversation; media failures retain voice/text path.
- Focused test: Denied media, network failure, video completion and interruption; no microphone ingestion of video audio.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-VIS-09 — Platform navigation and accessible controls

- Requirements: VR09
- Depends on: VC-VIS-04
- Scope: Retain access to memory and settings.
- Acceptance: iOS and Android use their native navigation conventions; Home/Memory/Settings remain accessible; Start/Stop is prominent and accessible despite the minimal ripple layout.
- Focused test: Test VoiceOver/TalkBack, native Back, safe areas and thumb reach on both platforms.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-VIS-10 — Visual memory and snapshot boundary

- Requirements: VR10
- Depends on: VC-VIS-07
- Scope: Clear transient displays and caches.
- Acceptance: Response/result cards are volatile and not a second history store; lock/signout/Stop clears them; private sessions persist no results, URLs or thumbnails; app-switcher snapshots are redacted.
- Focused test: Inspect JS/storage/caches/notifications and transitions using synthetic sensitive markers.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SEARCH-01 — Provider license privacy and cost assessment

- Requirements: SR01
- Depends on: None
- Scope: Select one documented authorized provider.
- Acceptance: Record search/media licensing, logging retention, region, attribution, credentials and funded usage limits before live queries; scraping is not assumed approved.
- Focused test: Review actual contracts/docs and cost envelope; unknown retention blocks production search.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SEARCH-02 — Explicit search authorization and query preview

- Requirements: SR02
- Depends on: VC-SEARCH-01, VC-VIS-04
- Scope: Confirm external requests.
- Acceptance: Search off initially; show or read the minimized outbound query and provider, obtain per-query confirmation; deny/cancel sends nothing and normal offline conversation continues.
- Focused test: Packet capture denied/cancelled requests and prompt injection attempting to bypass confirmation.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SEARCH-03 — Ephemeral query gateway

- Requirements: SR03
- Depends on: VC-SEARCH-02
- Scope: Protect provider credentials and minimize requests.
- Acceptance: An isolated HTTPS gateway accepts only the confirmed query and allowed media types, no transcript/account ID/memory/location; no body/query/response logs or database persistence; bounded timeouts and resource protections.
- Focused test: Schema negative tests, rate-limit responses, packet/log inspection and stale request cancellation.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SEARCH-04 — Untrusted result normalization

- Requirements: SR04
- Depends on: VC-SEARCH-03
- Scope: Validate and normalize result payloads.
- Acceptance: Treat external text as untrusted data; normalize source URLs/timestamps/license references and bounded snippets; reject unsafe URLs/scripts and never execute instructions from results.
- Focused test: Malicious snippets, huge payloads, private-network redirects, unsafe URL schemes and missing attribution fixtures.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SEARCH-05 — Safe media retrieval

- Requirements: SR05
- Depends on: VC-SEARCH-04, VC-VIS-08
- Scope: Minimize approved media network requests.
- Acceptance: Validate media types/size/redirects and permitted sources; no invisible tracking pixels or executable embeds; session-only caches cleared on expiry/lock/Stop; third-party disclosure occurs before loading.
- Focused test: Test content type mismatch, oversize file, blocked origin, cache clearing and hidden trackers.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SEARCH-06 — Offline and budget fallback

- Requirements: SR06
- Depends on: VC-SEARCH-04
- Scope: Return honest failures.
- Acceptance: Offline, provider failure, revoked consent or exhausted funded search capacity yields an explicit notice and local response; free offline conversation is not throttled and model knowledge is not labelled live search.
- Focused test: Test airplane mode, timeout,429,budget stop and revocation; core inference remains local.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SURFACE-01 — Android overlay feasibility

- Requirements: OR01
- Depends on: VC-AUDIO-09, VC-VIS-05
- Scope: Investigate real native overlay behavior.
- Acceptance: Test explicit display-over-other-apps permission and lifecycle on physical Android; unsupported or blocked surfaces fall back safely without opening Eilo automatically.
- Focused test: Permission deny/revoke, other-app overlay blocking, OEM variants, service termination and store-policy assessment.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SURFACE-02 — Android overlay presentation

- Requirements: OR02
- Depends on: VC-SURFACE-01, VC-VIS-07, VC-VIS-10
- Scope: Present authorized unlocked visual cards.
- Acceptance: Overlay off by default and separately consented; bounded movable card with close/pin/source and native Stop access; no full-screen takeover; underlying app remains usable.
- Focused test: Touch routing, Back/dismiss, gesture insets, inactivity and outside-app consent cases.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SURFACE-03 — iOS supported surface feasibility

- Requirements: OR03
- Depends on: VC-AUDIO-10
- Scope: Assess notifications and ActivityKit.
- Acceptance: No arbitrary Siri-style overlay claim; assess generic notification and eligible Live Activity behavior on devices, including authorization, system timing, background and App Review constraints.
- Focused test: Denied notifications, terminated app, actual supported surfaces and eligibility report; no simulator-only pass.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SURFACE-04 — iOS generic notification fallback

- Requirements: OR04
- Depends on: VC-SURFACE-03, VC-VIS-10
- Scope: Implement system constrained fallback.
- Acceptance: Unlocked iOS fallback says only results ready and offers explicit open; no personal response snippet; do not auto launch app, promise a20-second banner timer or embed rich video.
- Focused test: Test lock privacy, settings/revocation, tapping link and no automatic launch; system controls timing.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SURFACE-05 — Outside app lock and consent enforcement

- Requirements: OR05
- Depends on: VC-SURFACE-02, VC-SURFACE-04
- Scope: Centralize privacy boundary.
- Acceptance: Display consent does not grant microphone/background consent; locked display never shows replies, queries, images or history; generic operational status only; already-running audio availability remains platform dependent.
- Focused test: All combinations of mic/background/overlay/notification consent and lock; ensure no sensitive notification payload.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-SURFACE-06 — Native visual acceptance matrix

- Requirements: OR06
- Depends on: VC-VIS-10, VC-SEARCH-06, VC-SURFACE-05
- Scope: Run integrated device tests.
- Acceptance: Pass/fail/not-tested evidence covers foreground, Android overlay, iOS fallback, locked privacy, expiry, accessibility and media routes on each supported physical device.
- Focused test: Run deterministic fixtures and real-device journeys; unresolved privacy failure blocks release.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-DEVOPS-01 — Repository and board baseline

- Requirements: DP01
- Depends on: None
- Scope: Set up project management only when task authorized.
- Acceptance: GitHub confirmed public initially/private later; create board mapping stable IDs, dependencies and approval fields; no secrets or user data in public history.
- Focused test: Review board import and rules, secret scan and owner-only release authority.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-DEVOPS-02 — Focused pull request checks

- Requirements: DP02
- Depends on: VC-DEVOPS-01
- Scope: Configure CI scoped to affected components.
- Acceptance: Actions runs relevant lint/type/tests and native compile checks; sanitized synthetic artifacts only; no production credentials in pull-request jobs.
- Focused test: Trusted/untrusted PR checks, failed-check prevention and minimum permission review.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-DEVOPS-03 — Mobile build signing and staging

- Requirements: DP03
- Depends on: VC-DEVOPS-02
- Scope: Configure reviewed mobile distribution.
- Acceptance: Validate EAS custom native builds and signing; TestFlight/Play test tracks receive manually approved candidate builds with recorded SHA/config/artifact IDs.
- Focused test: Both platform compilation, signing inventory and restricted test installation; missing devices remain blocked.
- Status: planned / implementation not started / verification not run / task approval not requested.

### VC-DEVOPS-04 — Owner controlled release gates

- Requirements: DP04
- Depends on: VC-DEVOPS-03
- Scope: Define protected release authority.
- Acceptance: Record plan-dependent GitHub gates and private migration fallback; separate backend deploy/store upload/public release approval, secrets and compatibility-preserving migrations.
- Focused test: Dry-run unauthorized/failed-check paths and approval audit; no deployment during planning.
- Status: planned / implementation not started / verification not run / task approval not requested.


## Current verification amendments — 5 October 2026

These current focused tests supersede conflicting historical task wording.

- **VC-VERIFY-07**: Capture all app-process traffic with synthetic markers: search disabled/declined yields no conversational egress; confirmed search sends only the previewed minimized query; inspect SDKs, logs, caches and cancellation.
- **VC-AUTH-12**: Record real-device identity-only auth evidence separately from explicitly confirmed search traffic; reject auth/history coupling; design simulation is not a native pass.
