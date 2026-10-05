# Eilo MVP Specification

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

Current specification revision1.2 ·2October2026 · prior product baseline approved; Neon direction authorized; detail review pending

This specification defines the first version of a free, on-device voice companion for general conversation. Privacy is the primary release requirement. It follows stages 1–3 of the supplied Production Vibe Coding workflow: idea and problem, research, and specification. Architecture, implementation planning, development, and deployment have not started. Approval of this specification is not approval to implement it.

## 1 Idea and problem

### User problem

People want to talk naturally to a friendly assistant without typing, paying for each conversation, or sending private conversations to a provider. The first version should demonstrate a useful, responsive spoken conversation with explicit microphone control.

### Desired outcome

After setup and microphone permission, the user can address the companion by a wake phrase, speak naturally, receive a spoken reply, ask follow-up questions, and interrupt a reply. The app preserves conversation text and useful memories on the user’s device so it can maintain continuity across sessions. No conversation history or location history is sent to our servers. The interface stays simple, and an explicitly enabled listening mode should continue when the UI is not visible or the screen is off, where supported by the platform.

### Product constraints

- The core conversation is free to use, with no daily conversation quota proposed.
- Speech recognition, conversational inference, and speech synthesis run on the device. No cloud fallback is permitted in this version.
- Conversation history and derived memory may persist only in encrypted local storage. No cloud sync, app-managed cloud backup, remote conversation storage, or conversation upload is permitted in the MVP.
- Optional email/social sign-in with guest continuation: minimal remote account profile in Neon; Better Auth account service backed by Neon PostgreSQL only. Device authentication for protecting local memory is separate from an app account.
- Microphone permission authorizes access; it does not establish that every detected voice is addressing the app.
- Device compatibility and sustained performance remain unproven until later testing. The model research establishes candidates, not a validated product.
- Target both Android and iOS. React Native is the preferred provisional framework, subject to architecture assessment. Model selection, native integrations, supported device/OS versions, and implementation remain undecided. Background availability is a required feasibility investigation, not a validated guarantee.
- On-device training and optional privacy-preserving cloud learning are future research goals, not MVP functionality or authorization to upload data.

### Approved starting audience

English-speaking adults seeking casual conversation. This initial audience scope is approved. Child-focused design, multilingual support, and specialist advice require separate specifications.

## 2 Research and feasibility

### Existing solutions and gaps

System assistants demonstrate voice commands; cloud conversational assistants demonstrate fluid dialogue. This MVP focuses on private, local, friendly conversation. It does not claim unique capabilities, and market demand and willingness to install a model download still require user validation.

### Findings that affect the requirements

| Finding | Consequence for this specification |
|---|---|
| Compact local ASR and TTS candidates exist. Moonshine Streaming, Kokoro, and Pocket TTS were shortlisted in the preceding research. | Local operation is a credible direction; no particular stack is mandated yet. |
| Integrated conversational audio models exist, including LFM2.5-Audio. | Evaluate integrated and modular approaches after approval; licensing and runtime readiness remain selection criteria. |
| Published first-audio or transcription numbers exclude other stages of a conversation. | Measure complete user-turn-to-reply latency, with typical and slow results. |
| Mobile microphone access requires platform permission and lifecycle handling. Android places restrictions on background microphone services; Apple requires microphone permission and appropriate audio configuration. [S1–S3] | Include explicitly enabled background and screen-off operation as a platform feasibility gate. Permission alone does not allow arbitrary startup or system-assistant privileges. |
| Logs, backups, caches, and diagnostic tools can leak data despite an empty application database. OWASP explicitly treats these as mobile storage risks. [S4–S6] | Privacy acceptance tests cover all storage and network paths, not just database tables. |
| Voice playback can feed back into the microphone. Apple provides voice-processing APIs with echo cancellation. [S7] | Prevent self-triggering and verify interruption behaviour across supported audio routes. |

### Data and external services

MVP conversation and local memory require no remote API. Installation or setup may download model files; generic model distribution and optional identity-only authentication are the planned online services. It must be separate from conversational processing and local history. Optional identity operations are isolated; minimal account/profile and framework auth data persist in Neon PostgreSQL. The account service and providers process authentication information only. Future training uploads remain disabled and require a separate approved privacy specification. Download infrastructure can observe connection metadata such as IP addresses. No geolocation is derived, and no remote location or usage history is retained. Provider logging and retention must be reviewed before selection; an incompatible provider is a blocker, not a hidden exception to the privacy promise.

Model license approval must cover weights, runtimes, voices, phonemizers, redistribution, and commercial use, even if the app is free. Voice cloning is outside this MVP.

## 3 Specification

### Approved product decisions

The owner approved the remaining product choices on 1 October 2026. Framework selection remains provisional because React Native was expressed as a preference, not a final technical choice. Implementation feasibility and release evidence remain separate gates.

| Decision | Approved direction |
|---|---|
| Platform | Cross-platform Android and iOS; React Native provisionally preferred. Evaluate native integration and background support independently on both platforms. |
| Language | English initially. |
| Listening scope | Foreground use plus user-enabled background/screen-off listening where supported; stopped/force-quit/rebooted is not treated as listening. |
| Addressing the app | A configurable product wake phrase; “Hey Eilo” is a placeholder. No speaker enrollment or voiceprint. |
| Conversation memory | Encrypted on-device text history and derived memory across sessions, with review, deletion, and a private session mode. No saved raw audio. |
| Accounts | Optional email/password and Apple/Google sign-in with guest continuation; Better Auth account service backed by Neon PostgreSQL, minimal identity directory in Neon. Device authentication separately protects local memory. |
| Speech personality | Warm, concise, respectful, clearly presented as AI. |
| Online services | Generic model downloads and optional provider/relay authentication only. No conversational cloud processing. Future training participation requires separate opt-in and review. |

### Simple interface and main user journey

The home screen contains one central Start/Stop control, a compact status indicator, and access to Memory and Settings. There is no mandatory chat transcript or typing field. Memory and privacy controls may be secondary screens. Android’s ongoing service notification and platform microphone indicators cannot be hidden to make the UI look simpler.

1. Setup explains local processing, encrypted local text history, no saved audio, no cloud history, and the practical limits of background listening. Model download and compatibility checks happen before capture.
2. The user selects Start, grants microphone permission, and explicitly chooses whether listening should continue in the background. Background mode is off until selected; microphone permission is not its consent substitute.
3. The app enters wake-phrase standby. A persistent system-visible indicator/control remains wherever required. “Hey Eilo” is a placeholder phrase.
4. A wake phrase, including one spoken immediately before a question, opens an active conversation. Follow-ups require no wake phrase while that conversation is active.
5. Recognition, replies, speech synthesis, and retrieval from eligible local memory run on the phone. The user can interrupt or stop playback.
6. With history enabled, recognized user text and final reply text are committed to encrypted local history. Interrupted replies are marked as interrupted so future memory does not pretend the whole reply was heard. Unclear recognition is not silently promoted into a durable personal fact.
7. “End conversation” closes the active turn window, releases temporary context, and returns to standby while listening mode remains enabled. “Stop listening,” the Stop control, or the platform notification action releases the microphone and stops the mode entirely. Neither deletes saved history.
8. After 60 seconds without user speech, processing, or playback, the active session returns to standby. The timer starts when playback finishes. Background standby does not automatically expire after five minutes; it continues until stopped or interrupted by the platform, subject to the eventual battery budget.
9. Moving away from the UI or switching the screen off continues the explicitly enabled mode where supported. Without background consent, leaving the UI stops capture. Losing permission, force-stop, process termination, a call, or a service failure stops/pauses it safely; no promise of automatic revival is made.
10. Returning to the UI shows the actual listening state. If capture was terminated, the user must re-enable it. Reboot and force-quit never imply that listening remains available.

Wake detection is not identity verification. A bystander or television may activate it. “Phone asleep” means screen off/locked with an already-running permitted audio service; it does not mean powered off, force-stopped, or a process the OS has terminated.

### Background and locked-screen policy

Android documents a microphone foreground-service type that can continue capture in the background, with runtime permission and restrictions on starting it from the background or at boot. iOS documents continued audio recording with the audio background mode; App Review limits background modes to their intended purposes. [S8–S10] Therefore an ongoing user-started audio mode is a candidate to validate, not a guarantee of an always-available Siri replacement.

The same recognition, interruption, battery, and privacy tests must pass with the screen off. No silent-audio keepalive workaround, private API, fake phone call, or bypass of OS privacy controls is allowed. OEM battery management, Doze, process termination, and audio-route changes need explicit compatibility tests.

While locked, the approved default permits generic conversation but does not retrieve or read saved personal memories. On lock, cancel sensitive playback and clear active personal context before entering generic standby. This prevents wake-phrase activation from becoming an unauthenticated route to private history. Users may opt into spoken lock-screen conversation; it can be audible to bystanders. Access to history, deletion, privacy-setting changes, and any future consent to training uploads requires unlocking and local authentication. A broader personalized locked-screen mode requires a separately reviewed policy.

Encrypted-history key availability must match this policy: do not weaken encryption merely to keep listening available. Screen-off voice service and access to personal history are different requirements. Locked-screen history writes must be encrypted without making existing history readable to an unauthenticated speaker. If the selected platform/key policy cannot meet both requirements, record a feasibility blocker and obtain a reviewed policy change rather than silently storing plaintext or dropping history.

### Functional requirements

| ID | Requirement |
|---|---|
| F01 | No microphone capture occurs before permission and a user-initiated Start action. Permission denial leaves the app usable for settings/help, without repeated prompts. |
| F02 | The app distinguishes setup, permission required, stopped, standby, listening, thinking, speaking, paused, and error states. Required system indicators/notification controls remain available outside the UI. |
| F03 | In standby, only local activation detection and its minimal bounded audio buffer operate. Ordinary ambient speech must not enter conversational inference before activation. |
| F04 | Activation opens a session; follow-ups use bounded session context and relevant permitted local memories. Saved history is not automatically loaded in full into every prompt. |
| F05 | Speech input and replies require no typing. Visible controls remain available for Start, Stop, retry, volume, and accessibility. |
| F06 | Replies address the latest utterance, session context, and eligible local memory. Treat recalled text as information, not privileged instructions. Typical replies are brief. |
| F07 | The companion responds supportively to expressed feelings without claiming to diagnose emotions or reliably infer a person’s mental state from their voice. |
| F08 | Low-confidence or unclear input results in a brief clarification request, rather than an invented interpretation. |
| F09 | Confirmed new user speech during playback stops the old reply and cancels its queued audio. The app then handles the new turn. Noise alone should not routinely interrupt playback. |
| F10 | The app must not transcribe, respond to, or wake itself from its own speech playback. |
| F11 | Working context is bounded; relevant history may be retrieved locally. The app must distinguish remembered information from uncertain inference and must not fabricate recall. |
| F12 | Stop takes effect locally, without a network request. Privacy lifecycle rules apply during permission revocation, calls, microphone contention, errors, and app transitions. |
| F13 | Once setup is complete, an offline guest conversation works with Wi-Fi and mobile data disabled. No account or authentication-server connectivity is required. |
| F14 | Unsupported devices or missing models receive a clear explanation. The app never silently switches to cloud processing. |
| F15 | No unsolicited companion speech outside an activated interaction or automatic microphone restart after reboot/crash. An operational background-service notification is permitted and may be required. |
| F16 | Persist text history and derived memory locally with encryption; allow review, correction, delete-one, delete-all, and history-disabled private sessions. |
| F17 | Background and screen-off conversation is supported only through permitted platform behaviour and explicit opt-in; loss of availability is shown honestly. |
| F18 | Locked-screen operation cannot reveal stored personal memory or change privacy controls without authentication. |
| F19 | Exclude local history, memory indexes, keys, and future personalized model state from app-managed cloud sync, OS cloud backups, and device transfer. |

### Conversation boundaries

The app identifies itself as an AI companion. It does not claim to be human, demand exclusivity, or pressure users to keep talking. It can discuss ordinary topics, brainstorm, tell stories, and offer general suggestions based on its local model knowledge.

It must acknowledge uncertainty and lack of live information. It cannot promise current facts, professional diagnoses, emergency monitoring, or the ability to call for help. Responses to explicitly expressed imminent danger should encourage contacting local emergency services or a trusted person without collecting location or claiming an action was taken. Exact safety examples and human review criteria must be agreed before any public release.

### Privacy and data retention requirements

The privacy promise is now: **conversation history stays encrypted on this device; it is never sent to our servers in the MVP.** Do not advertise “we do not store conversations” without specifying that server storage is excluded but local history is intentionally retained. Temporary working memory remains necessary. Encryption protects stored data, not plaintext while an authorized app is using it, and does not eliminate risk from a compromised device.

| Data | Permitted handling | Retention rule |
|---|---|---|
| Ambient standby audio | Local wake detection; rolling buffer no longer than two seconds | Continuously overwritten, never recorded or transcribed into history |
| Active audio and generated speech | Local processing/playback in bounded memory | Release promptly; no audio files |
| User/reply text, session time, interrupted status | Encrypted app-private local history | Approved 90-day default, configurable; no server copy |
| Derived facts, summaries, retrieval indexes/embeddings | Encrypted locally; provenance links to source messages | User can inspect/correct/delete; source expiry/deletion removes or regenerates dependent memory |
| Temporary prompts and inference caches | Working memory only | Release at session end, Stop, termination, and privacy transitions; no diagnostic dump or persistence |
| Voiceprints, automatic emotional profiles | Not collected | None |
| Location, contacts, photos, call history | Not accessed | No corresponding permissions |
| Generic model files | Verified persistent local files | Until update/removal; not personalized from user content in MVP |
| Preferences | Local language, voice, volume, history and background settings | Until reset/uninstall; no remote behavioural profile |
| Remote user/account details | Optional issuer/subject and lifecycle tokens only; see revision below | Minimal Neon identity/session database; provider processing disclosed |
| Future local training datasets/adapters/checkpoints | Future feature only; encrypted local personal data | Must obey separate opt-in, deletion and reset rules; upload is disabled in MVP |
| Analytics, session replay, advertising IDs, conversational crash reports | Prohibited | None |
| Network metadata for model downloads | Transient routing/security processing | No retained user IP/location/usage history; review vendor behaviour before selection |

The approved local storage limit is 250 MB for history and derived memory, excluding generic model files. Notify before reaching it and offer deletion/retention controls; never silently upload, silently discard recent history, or crash. The owner approved the 90-day default and 250 MB limit on 1 October 2026. Approved capacity policy: notify before the limit and offer deletion or shorter retention; no silent deletion outside the selected retention policy. Precise thresholds and storage-full transaction behaviour are architecture-stage details.

History saving is enabled only after the onboarding disclosure and a clear user choice. Private sessions do not write transcripts, summaries, embeddings, or training examples. Switching private mode does not erase older history; Delete all is separate. No automatic cloud backup or sync is offered. Device loss or uninstall can mean permanent history loss; disclose this in setup. Manual export/transfer is deferred to avoid introducing an unreviewed leakage path.

A request to delete a conversation removes its local text, associated cached results, and dependent derived facts/index entries. Delete all clears history, memory, and any future personal adapter. Local deletion makes data inaccessible through app interfaces immediately; encrypted-storage handling must address journal/temporary copies and keys. Do not promise byte-level forensic erasure on flash storage. For future training, deleting source messages cannot guarantee removal of their influence from existing weights; reset the adapter and retrain only from remaining authorized data.

Optional social identity now has a separate sign-out/revocation/deletion workflow. Onboarding consent and settings stay locally. A device change does not rehydrate history through login. See the authentication amendment below.

### Security requirements

| ID | Requirement |
|---|---|
| S01 | Core speech/inference/history content never leaves the device through runtimes, speech APIs, telemetry/support/crash reporting. Only a separately previewed and explicitly confirmed minimized search query may leave under SR01-SR06; no transcript, stored memory or cloud inference. Offline system speech must be verified. |
| S02 | Conversation data persists only in the declared encrypted local history/memory store and necessary encrypted storage journals. No plaintext temporary files, logs, notification previews, diagnostics, cloud backups, or device-transfer copies. |
| S03 | Logging is disabled for conversational input/output in development and production. Later tests use synthetic conversations and must not record real-user content. |
| S04 | No conversation content in app-switcher snapshots or lock-screen notifications. History screens require an unlocked/authenticated device; optional live captions are local and hidden at lock. |
| S05 | Downloaded models are integrity-checked against trusted release metadata. Model/voice licenses and dependencies must be reviewed before inclusion. |
| S06 | Model downloads use authenticated encrypted transport and integrity verification. Local encryption credentials use platform secure storage. No service secrets are embedded in the app. |
| S07 | There are no conversation upload endpoints or remote user/conversation databases. Authentication-only endpoints are isolated from conversation and backed by Neon account data. Access to local memory and privileged privacy actions requires the specified device authentication. |
| S08 | Unauthorized persistence or conversation/memory transmission blocks release. The sole content-egress exception is the separately confirmed minimized query under SR01-SR06; its scope/retention/provider evidence is release gated. |
| S09 | History, derived memory, and future personal adapters are encrypted at rest with platform-protected keys and authenticated integrity protection. Review key accessibility while locked. |
| S10 | Deleting source data must invalidate derived memory. Stored conversations never override system privacy/safety rules. |

### Edge cases and required behaviour

| Situation | Behaviour |
|---|---|
| Permission denied or revoked | Stop/refrain from capture; explain the setting; do not loop permission requests. |
| App backgrounded or screen locked | Continue only the permitted enabled mode; on lock cancel private playback/context and disallow stored-memory retrieval. Without background consent, stop capture. |
| Call, permission loss, OS termination | Pause/stop audio and release temporary state; retained encrypted history remains. Show actual availability; require a user action if the service must be restarted. |
| Another app controls the microphone | Show the unavailable state; no fabricated listening indicator. |
| Silence, noise, or uncertain speech | Do not invent a question; ask for repetition only during an active session. |
| Television or bystander says wake phrase | Possible false activation is disclosed; activation cue and Stop remain available. No voice identity claim. |
| Multiple overlapping speakers | Ask for one speaker at a time if input is unclear; no speaker enrollment. |
| Headphones disconnect or Bluetooth route changes | Pause and require confirmation before moving private playback to the phone speaker. |
| User interrupts a reply | Cancel previous playback and pending reply; preserve only appropriate session context. |
| Recognition or generation fails | Give a short local error if safe; do not repeat sensitive input or enable cloud fallback. |
| Memory pressure, low battery, or thermal limits | Pause/stop safely with an explanation; release working context; preserve existing encrypted history without unencrypted spill or cloud fallback. |
| Crash or forced termination | Restart with microphone stopped. Previously committed encrypted history remains; prevent corrupt/partial writes from being treated as trusted memory. No plaintext conversation diagnostics. |
| User asks for browsing, calls, or photos | Explain that the capability is unavailable in this version; do not request extra permissions. |

### Approved provisional performance and quality targets

The owner approved these as provisional acceptance targets, not claims of achieved performance. They apply to a declared device/OS matrix to be agreed during architecture review. Privacy requirements cannot be relaxed to meet them.

| Measure | Proposed target and method |
|---|---|
| Complete spoken response delay | Median at most 1.5 seconds and 95th percentile at most 3 seconds, from annotated end of user speech to first meaningful reply audio, excluding filler acknowledgements; include endpoint detection and all inference stages |
| Interruption | Playback stops within 300 ms at the 95th percentile from annotated onset of intelligible user interruption on the supported test conditions |
| Wake detection | At least 95% detection in the agreed quiet-room set; no more than one false activation per eight hours of the agreed ambient/no-wake audio set |
| Recognition | At most 10% word error rate on an agreed representative English set; evaluate accents, names, numbers, and noise separately |
| Conversation quality | At least 90% acceptable outcomes across 100 prewritten multi-turn conversations, scored by a human rubric for relevance, continuity, clarity, and tone; privacy/safety cases have separate pass/fail gates |
| Sustained use | Complete a 60-minute conversation test in foreground and screen-off modes without crash/thermal shutdown; final-15-minute latency meets the targets |
| Background standby | Evaluate eight hours screen-off for wake availability, false activation, battery consumption, Doze/OEM restrictions, and honest stopped-state reporting; no all-day availability claim before testing |
| Memory retrieval | Relevant remembered facts pass agreed cross-session recall tests; deleted/expired facts never reappear through retrieval |
| Battery and memory | Measure battery percentage consumed per hour, peak memory, download size, and storage footprint on each supported device. Numerical release budgets remain an explicit architecture-stage decision, not an assumption |

False activation scores do not imply resistance to a deliberately spoken wake phrase. Test datasets, sample sizes, supported audio routes, hardware, and scoring procedure must be frozen before verification. A missed target results in a reviewed scope or device-support change, not an unreported exception.

### Acceptance criteria

| ID | Scenario and observable pass condition |
|---|---|
| A01 | Fresh install: inspect capture state before Start and before permission; no audio capture occurs. Permission denial leaves capture stopped. |
| A02 | Granted permission: ordinary speech during standby produces no conversational response; the configured wake phrase activates a session with a visible/audible cue. Evaluate false activation separately. |
| A03 | Wake phrase plus question in one sentence receives a relevant answer without repeating the question. |
| A04 | With history enabled, a synthetic fact survives Stop/restart and is recalled appropriately after unlock. Delete the source and dependent memory; the fact no longer appears through retrieval. Private-session facts never persist. |
| A05 | User interrupts spoken output; old audio and queued output stop within the target and the new request is handled. Playback does not trigger recognition of itself. |
| A06 | Stop releases capture; active-session timeout returns to standby. Enabled background mode continues on UI exit/lock where permitted. Calls, revocation, termination, and failures obey the revised lifecycle policy without deleting committed history. |
| A07 | With setup complete and search disabled or declined, guest conversation works offline and emits no conversation-dependent requests. Separately confirmed search may send only the minimized previewed query under SR02-SR06; no transcript/history upload or cloud inference. |
| A08 | Synthetic markers appear only in the encrypted local store and authorized in-memory processing. Inspect files, journals, logs, diagnostics, backups and transfer/restore results for prohibited plaintext/copies. Test encryption and backup exclusions; a clean text search alone is insufficient. |
| A09 | Restart on the same phone preserves authorized local history; cloud backup/device transfer never restores it or its keys. Local deletion/reset and private-mode behaviour meet the specified policy. |
| A10 | Guest setup and normal use require no sign-up/login. Optional sign-in has identity-only provider/relay traffic and minimal identity directory in Neon or conversation endpoints. Device authentication still protects local history. |
| A11 | Headphone disconnection does not unexpectedly play private replies through the speaker. Missing models and unsupported devices never trigger cloud fallback. |
| A12 | Run agreed performance, activation, quality, memory-recall, background, and 60-minute tests on each supported configuration; report distributions and failures. |
| A13 | Start mode while visible, leave UI, lock screen, and speak the wake phrase: generic conversation works on supported devices without reopening UI. Repeat under declared idle/battery conditions; no private memories are revealed while locked. |
| A14 | Force-stop, reboot, kill the service, and remove permission: no claim that wake listening remains available. Restart requires a permitted user action. |
| A15 | Notification/voice Stop works without opening the app. Requests to read history, delete it, or change privacy settings while locked require unlock/authentication. |
| A16 | Training and all model-update upload paths are absent/disabled in MVP; network inspection confirms no history or personal model state leaves the phone. |

No acceptance tests have been run. These criteria specify what later verification must demonstrate.

### Non-goals

- Unrestricted system-assistant privileges, guaranteed listening after force-quit/reboot, and bypassing OS background restrictions.
- Calls, messaging, camera access, contacts, location, navigation, or controlling other apps.
- Unconfirmed/continuous web search, retrieval from personal files and location-based automation. Confirmed optional live search is now in revised scope under SR01-SR06; external-provider gates apply.
- Cloud conversation history, cloud sync, manual history export, and cross-device memory. Local text history and cross-session memory are in scope.
- Voice cloning, biometric speaker identification, or automatic emotion diagnosis.
- Advertising, analytics SDKs, session replay, or any conversation-based model training/upload in the MVP. Future training is a research goal below.
- A therapist, medical service, emergency monitoring system, or child-focused companion.

## 4 Future personalization and training research

This section records the requested future goal. It does not move the current workflow into architecture or development and does not authorize training or cloud uploads.

### Distinguish memory from training

Local memory retrieves selected past facts without changing model weights. This should be evaluated first for names, preferences, and conversational continuity. Training changes the model’s behaviour; it is not necessary just to remember a favourite movie, and a chat transcript is not automatically a good training example.

A future experiment could use a small personal adapter (for example LoRA) rather than repeatedly training/uploading an entire model. Official MLX examples demonstrate LoRA and quantized LoRA, but that is not a validated training benchmark for our chosen phone/audio stack. [S11] Training support, peak memory, battery/heat, licence, data sufficiency, and background scheduling need device-specific research. Ability to run inference does not establish ability to train efficiently.

### Future options and privacy implications

| Approach | What leaves the phone | Assessment |
|---|---|---|
| Local memory and retrieval | Nothing personal | Recommended MVP path for continuity |
| Local adapter training | Nothing personal | Future device-feasibility experiment; explicit opt-in |
| Upload individual tuned model/adapter for cloud refinement | User-derived parameters; possibly training examples if requested | Technically possible with compatible formats and a training objective, but changes the privacy boundary and adds cloud costs; not approved |
| Federated learning | Protected updates for aggregation across participating devices | Future research candidate for improving a shared model; requires privacy controls, not merely omitting raw transcripts |
| Cloud refinement of a generic model using public/licensed data | No user personal state | Compatible with local-only personal data, subject to model update validation |

A cloud server cannot automatically improve a personal model merely by receiving its weights: it still needs a defined training objective, appropriate data or aggregate updates, and evaluation. Personalized adapters from incompatible base versions cannot simply be averaged or merged.

Model weights and updates are potentially sensitive. Published gradient-leakage work shows training data can be reconstructed in some settings. [S12] Federated learning is not inherently anonymous or a guarantee of zero leakage. Google’s research combines secure aggregation and differential privacy for stronger protections. [S13] Secure aggregation hides individual updates from the aggregator under its threat model; differential privacy limits individual influence at a cost to utility. Both require a concrete protocol and measured privacy accounting.

Uploading a whole personal model, even temporarily and even outside a database, is cloud processing of user-derived information. Thus “only user details in our DB” is insufficient as a privacy guarantee. Object storage, job buffers, checkpoints, logs, and backups would also need explicit policy. We cannot describe such a future mode as “no personal data ever leaves your device.”

### Gates before any training feature

- Separate opt-in for local training and for cloud contribution; off by default, revocable, never required for free conversation.
- Train only on authorized, curated text/corrections or feedback. Exclude private sessions, ambient/bystander recordings, unclear transcripts, and deleted content. Do not train on the assistant’s own unverified outputs by default.
- Run only under approved charging, battery, thermal, and OS scheduling conditions; stop safely when interrupted. No promise of continuous or nightly completion before tests.
- Keep a generic base model plus versioned personal state; evaluate each candidate against the previous model for usefulness, privacy leakage, safety, and regression before activating it. Support reset and rollback.
- Treat personal adapters/checkpoints as encrypted sensitive data. Deleting source text may require discarding and rebuilding the adapter; targeted machine unlearning is not assumed.
- For federated work, approve the threat model, clipping/noise/privacy budget, aggregation cohort size, dropout handling, secure aggregation, participation metadata, server retention, poisoning protection, and cost. No individual-adapter upload as an unreviewed shortcut.
- Explain that deleting a contribution after it has influenced a shared model is not automatically possible. Opt-out stops future contributions; removal guarantees require separate research and accurate disclosure.

Recommended progression: local history and retrieval first, a measured local-adapter pilot second, and optional federated learning only if there is a demonstrated benefit and an approved privacy design. Cloud refinement remains possible research, not a confirmed feature or an MVP dependency.

## Approval and next gate

The guest-only baseline was approved on 1 October 2026. The current Eilo authentication amendment is awaiting review. The following list reflects the revised proposal, not retroactive approval:

- Android and iOS cross-platform support, with React Native a provisional preference to assess during architecture.
- English initially, adult starting audience, and optional email/social sign-in plus guest use with minimal Neon account database.
- Explicit history consent, local private sessions, source-aware deletion, and local encrypted persistent memory.
- Ninety-day default retention and 250 MB limit for history/derived memory, excluding generic model files. At capacity, notify and offer deletion/shorter retention; no silent deletion outside the selected policy.
- Separately enabled background listening with required status/Stop controls; generic locked-screen conversation without stored personal-memory access.
- The stated performance targets remain provisional until device testing. No relaxation of privacy requirements to achieve them.

Architecture is the next workflow stage. Its review must settle model/runtime selection, the React Native/native boundary, supported device/OS versions, encrypted storage/key accessibility, screen-off and background lifecycle behaviour on both platforms, capacity handling, battery/memory budgets, and detailed verification/safety procedures.

The principal feasibility risk remains platform-compliant screen-off operation, particularly parity across Android and iOS. It is a required investigation gate, not silently dropped functionality. If it fails on either platform, present evidence and seek a reviewed scope change before claiming support. Choosing a cross-platform UI framework does not establish equal operating-system capabilities.

No acceptance tests have been run, and no app architecture, source code, training, dependency installation, or deployment has begun. This approval completes the product specification review. It does not authorize app development or personal-data uploads. Architecture and an incremental implementation plan must be reviewed before development, preserving the requested human approval gates.

## Sources

The supplied workflow image is the stage-order reference. The preceding model comparison supplies the candidate shortlist; selection remains deferred.

- S1 Android microphone/background restrictions: https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- S2 Android runtime permissions: https://developer.android.com/training/permissions/requesting
- S3 Apple microphone permission: https://developer.apple.com/documentation/avfaudio/avaudioapplication/requestrecordpermission(completionhandler:)
- S4 OWASP mobile storage requirements: https://mas.owasp.org/MASVS/05-MASVS-STORAGE/
- S5 OWASP sensitive information in logs: https://mas.owasp.org/MASWE/MASVS-STORAGE/MASWE-0005/
- S6 Android backup behaviour: https://developer.android.com/identity/data/autobackup
- S7 Apple voice processing: https://developer.apple.com/documentation/avfaudio/using-voice-processing
- Candidate registries: https://huggingface.co/moonshine-ai/moonshine-streaming-small ; https://huggingface.co/hexgrad/Kokoro-82M ; https://huggingface.co/kyutai/pocket-tts ; https://huggingface.co/LiquidAI/LFM2.5-Audio-1.5B

- S8 Android microphone foreground-service requirements: https://developer.android.com/develop/background-work/services/fgs/service-types#microphone
- S9 Apple background recording: https://developer.apple.com/documentation/AVFAudio/AVAudioSession/Category-swift.struct/record
- S10 Apple App Review background use and capture disclosure: https://developer.apple.com/app-store/review/guidelines/ (sections 2.5.4 and 2.5.14)
- S11 Official MLX Swift LoRA example: https://github.com/ml-explore/mlx-swift-examples/blob/main/Tools/llm-tool/README.md
- S12 Deep Leakage from Gradients research: https://arxiv.org/abs/1906.08935
- S13 Distributed differential privacy for federated learning: https://research.google/blog/distributed-differential-privacy-for-federated-learning/



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

## Revised requirement text for the merged scope

| ID | Requirement |
|---|---|
| VR01 | Rounded blue/lavender ripples animate only during listening and speaking; stopped, standby and thinking remain distinct and truthful. |
| VR02 | One-second loop is the requested preview and initial adjustable design parameter; reduced motion freezes decoration; light/dark text and controls meet defined contrast and platform scaling targets. |
| VR03 | Without rich content, spoken clauses appear progressively in the foreground; unspoken cancelled output is excluded and interruption is labelled. |
| VR04 | Text defaults on, images/video off; Voice only disables all visuals while retaining previous individual choices; voice changes apply only in an active authorized session. |
| VR05 | Allowed rich results replace the default text card, with recoverable spoken answer, source attribution and explicit media availability; no invented ratings, travel time or current facts. |
| VR06 | Dismiss after 20 seconds with no speech, processing, loading, interaction, accessibility focus or video playback; each relevant event resets timer; dismissal never stops listening. |
| VR07 | Keep visible pins only the current session/card; dismiss remains available; a new query, Stop, lock or privacy epoch clears old content and stale callbacks cannot reopen it. |
| VR08 | No video autoplay; playback begins by tap; Eilo pauses speech and listening during video, clearly exposes Resume conversation; media failures retain voice/text path. |
| VR09 | iOS and Android use their native navigation conventions; Home/Memory/Settings remain accessible; Start/Stop is prominent and accessible despite the minimal ripple layout. |
| VR10 | Response/result cards are volatile and not a second history store; lock/signout/Stop clears them; private sessions persist no results, URLs or thumbnails; app-switcher snapshots are redacted. |
| SR01 | Record search/media licensing, logging retention, region, attribution, credentials and funded usage limits before live queries; scraping is not assumed approved. |
| SR02 | Search off initially; show or read the minimized outbound query and provider, obtain per-query confirmation; deny/cancel sends nothing and normal offline conversation continues. |
| SR03 | An isolated HTTPS gateway accepts only the confirmed query and allowed media types, no transcript/account ID/memory/location; no body/query/response logs or database persistence; bounded timeouts and resource protections. |
| SR04 | Treat external text as untrusted data; normalize source URLs/timestamps/license references and bounded snippets; reject unsafe URLs/scripts and never execute instructions from results. |
| SR05 | Validate media types/size/redirects and permitted sources; no invisible tracking pixels or executable embeds; session-only caches cleared on expiry/lock/Stop; third-party disclosure occurs before loading. |
| SR06 | Offline, provider failure, revoked consent or exhausted funded search capacity yields an explicit notice and local response; free offline conversation is not throttled and model knowledge is not labelled live search. |
| OR01 | Test explicit display-over-other-apps permission and lifecycle on physical Android; unsupported or blocked surfaces fall back safely without opening Eilo automatically. |
| OR02 | Overlay off by default and separately consented; bounded movable card with close/pin/source and native Stop access; no full-screen takeover; underlying app remains usable. |
| OR03 | No arbitrary Siri-style overlay claim; assess generic notification and eligible Live Activity behavior on devices, including authorization, system timing, background and App Review constraints. |
| OR04 | Unlocked iOS fallback says only results ready and offers explicit open; no personal response snippet; do not auto launch app, promise a20-second banner timer or embed rich video. |
| OR05 | Display consent does not grant microphone/background consent; locked display never shows replies, queries, images or history; generic operational status only; already-running audio availability remains platform dependent. |
| OR06 | Pass/fail/not-tested evidence covers foreground, Android overlay, iOS fallback, locked privacy, expiry, accessibility and media routes on each supported physical device. |
| DP01 | GitHub confirmed public initially/private later; create board mapping stable IDs, dependencies and approval fields; no secrets or user data in public history. |
| DP02 | Actions runs relevant lint/type/tests and native compile checks; sanitized synthetic artifacts only; no production credentials in pull-request jobs. |
| DP03 | Validate EAS custom native builds and signing; TestFlight/Play test tracks receive manually approved candidate builds with recorded SHA/config/artifact IDs. |
| DP04 | Record plan-dependent GitHub gates and private migration fallback; separate backend deploy/store upload/public release approval, secrets and compatibility-preserving migrations. |
