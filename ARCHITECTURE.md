# Eilo — Architecture and Technology Contract

Version 1.0 | 5 October 2026

## Framework and exact responsibility boundaries
| Layer | Selected direction | Rules |
|---|---|---|
| Mobile UI | React Native New Architecture + TypeScript strict mode; native Android/iOS projects | Functional components, Codegen/TurboModule interfaces; no Expo Go-only implementation. Pin supported versions during an authorized setup task. |
| Navigation | React Navigation, native-stack/bottom-tab patterns | Home/Memory/Settings and native modal/account flows; screen state never owns background capture. |
| Styling | React Native StyleSheet + semantic Design 2.0 tokens | System fonts, light/dark roles, accessible stable surfaces. Do not introduce NativeWind/Tailwind/styled-components as competing systems. |
| JS state | Zustand for non-sensitive UI preferences/navigation presentation only | Component-local state for local interaction. Native controller is sole audio/privacy authority. Do not use Redux/MobX/Jotai or parallel global Context state. |
| Native Android | Kotlin | Audio/lifecycle/foreground service, Keystore, authenticated memory and permissioned surfaces. |
| Native iOS | Swift | AVAudioSession/audio I/O, protected data/Keychain/local authentication and supported notifications. |
| Inference core | In-process C++ through pinned llama.cpp and native model adapters | No local HTTP server, Python, WebView inference or cloud fallback. |
| ASR evaluation | Moonshine Small Streaming English | Exact artifact/native binding/license/performance must be validated; not a production pass. |
| LLM evaluation | Qwen3-1.7B GGUF Q4_K_M, non-thinking | Chat-template configuration must actually disable thinking. Qwen3-0.6B is a comparison candidate only. |
| Wake/VAD | Native keyword spotting compatible with sherpa-onnx + native VAD | Exact checkpoint, phrase, licenses and thresholds are open tasks. No fabricated selection or continuous ambient transcript. |
| TTS | Installed offline English platform voices | AVSpeechSynthesizer/Android TextToSpeech; confirm offline assets and prevent network voice fallback. Kokoro deferred. |
| Personal storage | Native SQLCipher + OS-protected device-only keys | No plaintext history, JS storage, cloud database or key material crossing bridge. |
| Identity service | Node.js + TypeScript + Better Auth + Neon PostgreSQL | Separately hosted service. Email/password/Google/Apple; verified native OAuth integration, minimal account/auth/session data only. |
| DB ownership | Better Auth owns framework auth migrations; Drizzle owns explicitly defined app-profile migrations | One controlled migration pipeline; no second ORM or invented hand-written auth schema. Adapter compatibility is an implementation gate. |
| Search | Isolated TypeScript gateway with provider adapter | No provider selected yet. Validate bounded confirmed payload, protect server credentials, avoid body logging/persistence; no account subject/history DB dependency. |
| Delivery | GitHub, Actions; EAS Build/Submit candidate; Vercel Node hosting candidate; Neon | Versions, hosting compatibility, region/retention and costs require verification. Docker is optional for services and does not replace macOS/Xcode. |

React Navigation, Zustand, StyleSheet, Drizzle, npm workspaces and Vitest conventions below are new documentation choices to reduce ambiguity. Verify compatibility before adding packages during authorized setup. Do not install packages in this documentation phase or invent lockfile versions. Existing approved native boundaries override convenience libraries.

## Future folder structure (do not create code now)
- apps/mobile: UI, typed native interface clients and non-sensitive presentation state.
- services/identity: Better Auth service, minimal profile/account lifecycle and migrations.
- services/search: independent query/result contract/provider integration; no identity DB permissions.
- packages/contracts: runtime-validated shared account/search/event DTOs.
- packages/design-tokens: semantic Design 2.0 roles adapted from the baseline JSON.
- docs/baseline: source design/spec/backlog/history and evidence index.
- Native Kotlin/Swift/C++ ownership follows React Native module/project conventions; finalize paths in the scaffold task instead of scattering duplicate engines.

Use npm workspaces with one lockfile and documented Node/npm versions. TypeScript/ESLint/Prettier configuration belongs to authorized scaffolding. JS pure logic and services use Vitest; RN UI tests use React Native Testing Library with the required compatible runner. Android native tests use JUnit; iOS native tests use XCTest. Physical lifecycle/storage/audio tests remain mandatory where simulators or unit tests cannot establish behavior. Avoid redundant runners in the same package.

## Native control and data flow
The controller owns microphone capture, wake/turn state, generation IDs, privacy epochs, cancellation, speech policy, memory access and display expiry. React Native sends typed commands and observes snapshots/events. It does not stream PCM through JS, keep the service alive with timers, authenticate lock access or hold decrypted keys.

Pipeline: wake → native streaming ASR → privacy check → bounded local prompt/eligible memory → local LLM → approved speech clauses → offline TTS. Inputs/retrieved text are untrusted. Initial evaluation budgets: 4,096-token context, at most 512 retrieved-memory tokens, normally 256 generated reply tokens. They are tuning hypotheses, not quality evidence.

Every async output is bound to generation, session and privacy epoch. Revalidate before display, playback or persistence. Stop/lock/identity changes invalidate stale work. UI response text contains only clauses released for speech. Temporary authenticated Memory views may cross to JS for display, must be paginated/volatile and cleared on transitions; they are not stored in Zustand or a query cache.

## Storage and credentials
SQLCipher stores consented history, source-linked facts and indexes locally. Device-only protected keys are accessed through native authenticated sessions and never JS/AsyncStorage. Main store closes and owned decrypted buffers clear at lock. A sealed ciphertext inbox for consented locked-turn writes is proposed, not implemented: vetted envelope encryption, locked-inaccessible private key, atomic authenticated import and quota/expiry enforcement require review. If impossible, raise a policy blocker rather than keep the history key unlocked.

Generic model assets use verified manifests/checksums, exact license inventories and atomic staging/update/rollback. They are separate from personal storage. Model downloads are allowlisted network operations, not permission to upload personal data.

## API and migration contract
No endpoints or tables are implemented. First define runtime-validated schemas and error envelopes using synthetic fixtures. Account profile GET/PATCH and authenticated deletion/status routes match baseline semantics; email/identity are server-derived. Proposed route paths in the management plan are contracts to verify, not live services. Better Auth generates its own compatible auth schema; no custom password hashing/token protocol.

Account tables must not contain conversations, memory, queries, media, location or personal models. Record consent/preferences locally unless a separately approved identity/legal purpose requires a minimal server record. Migrations are additive/backwards-compatible where needed, tested on disposable synthetic DBs and reviewed. Creating/applying a remote migration or provisioning Neon is a separate human-authorized action.

Search accepts only a confirmed bounded query and selected categories with a random per-request identifier, not an account ID. Gateway rejects unexpected fields; enforce size/timeout/origin/redirect/content limits and cost controls. Provider credentials remain server-side. Search gateway lacks Neon write credentials. Results are normalized source data, not trusted commands. Review provider retention/licensing/cost before live activation.

## Service separation and fallback
Core conversation has no networking dependency. Identity, generic model download and explicit query/media clients have separate adapters and capabilities. A component boundary does not create per-component OS network permissions: audit actual traffic. Keep authenticated personal state out of network-request enrichment, error reporting and tracing.

Provider outage, quota limit or overlay rejection preserves core offline conversation. iOS outside-app rich rendering does not exist as a guaranteed arbitrary overlay; use generic permitted notifications unless separately approved eligible system surfaces pass review.

## Version and decision discipline
Record dependency name, exact resolved version, runtime/native compatibility, license and reason in setup evidence. No unpinned latest tags or silently chosen provider. Environment names/settings are documented without secret values. Model/provider replacements, new state systems, remote data classes or privacy changes need a scoped decision and human review before implementation.

## S04 Android foreground capture decision
Device initialization/start is asynchronous on a process-owned native executor. ControllerEffects.beginCapture reports completion/failure back to the serialized Kotlin controller; an outstanding Start has no generation and never reports standby before confirmation. Stop cancels the request and rejects its late callback. Android AudioRecord uses 16 kHz mono PCM16, a bounded platform buffer and a reused 320-sample native buffer. Nonblocking reads and immediate sample erasure share the capture lifecycle monitor; this task discards samples until separately approved wake/ASR integration. There is no JS PCM event, file sink, upload, startup capture or background service. Foreground visibility, current OS permission, device unlock and the existing model-readiness gate are required. Swift remains unchanged until VC-AUDIO-05.

Android build compatibility minimum is API 26 because the S03 integrity/atomic file operations use java.nio.file; the prior template minimum of 24 was inconsistent. This does not certify performance/privacy/audio behavior on API 26 devices or change the proposed Android 15+/8 GB evaluation cohort.
