# Eilo

**“I am here for you.”** Eilo is an English, voice-first mobile companion being built for Android and iOS. Its core conversation pipeline is intended to run on the phone, without a per-minute cloud inference dependency. Optional accounts and explicitly confirmed online searches are separate capabilities.

## The problem we are solving

Talking to a companion should be easy without repeatedly typing or navigating screens. A cloud-dependent voice experience can introduce recurring inference costs, connectivity requirements and unnecessary exposure of personal conversations. Eilo aims to provide a free core experience with local speech recognition, response generation and speech output, while keeping personal history under device protection and explicit consent.

The intended journey is: complete onboarding, install verified model assets, choose a privacy mode, explicitly start listening, speak to Eilo and hear its reply. Guests can use the core without signing in. Optional accounts must not become a requirement for offline conversation.

Eilo is a consumer companion. It does not diagnose emotions or provide medical or emergency care. Local inference and encryption are design requirements, not claims of completed security, legal compliance or device feasibility.

## Current implementation

The repository contains a React Native application, shared contracts/design tokens, native controller and capture integrations, a verified model-installation foundation and synthetic test harnesses.

| Area | Current state |
| --- | --- |
| S01: foundation | Mobile shell, workspace, contracts, native test seams and CI. |
| S02: controller/privacy contracts | Reviewed; native state and cancellation boundaries implemented. |
| S03: model installation | Reviewed; signed-manifest, checksum, staging/resume/activation and readiness mechanisms implemented. Production distribution configuration remains unavailable. |
| S04: guest/audio setup | Reviewed and merged; explicit consent, native control and capture foundations implemented. Physical/background feasibility blockers remain. |
| S05 / VC-TURN-01 | Reviewed and approved: bounded native standby audio buffers. Later S05 tasks remain outstanding. |
| S05 / VC-TURN-02 | Adapter checkpoint reviewed and merged. Runtime evaluation under review; synthetic target recognition failed and microphone integration remains gated. [Evidence](Eilo/docs/sprints/S05_VC_TURN_02_RUNTIME_REVIEW.md). |
| Wake/VAD, streaming ASR, local replies, offline TTS and protected history | Planned pipeline; not a completed integrated voice experience. |

**The current app is not an end-to-end conversation demo.** Production model trust, download origins and license approvals are not configured. Start remains gated by native readiness; do not bypass it to present a synthetic fixture as a working product. History selection does not enable encrypted storage that has not been implemented.

VC-TURN-01 keeps at most two seconds of audio samples in fixed-capacity native rings. Overwrites erase old slots, timestamps expire stale samples, Stop clears retained samples and run tickets reject callbacks from earlier captures. Android uses mono PCM16 at 16 kHz; iOS uses the first Float input channel at its validated actual rate. PCM does not cross the JavaScript bridge or go to files, ASR or a model in this task. OS scheduling can delay timer-driven erasure; physical timing is unverified.

## Repository layout

```text
.
├── README.md                   Project overview and reproduction guide
├── .github/workflows/          Hosted validation
├── .gitleaks.toml              Secret-scanning configuration
├── planning/                   Sprint mapping and historical setup evidence
└── Eilo/                       npm workspace; run JavaScript commands here
    ├── apps/mobile/            React Native app, Android and iOS projects
    ├── packages/contracts/    Validated metadata contracts
    ├── packages/design-tokens/ Semantic UI tokens
    ├── packages/native-test-seam/ Swift source and synthetic XCTest fixtures
    ├── scripts/               Scoped workspace tooling
    ├── tools/model-pack/      Model-pack recipes and tooling
    └── docs/                  Sprint evidence, model contracts and device matrices
```

The local knowledge-transfer package, its ZIP and root decision/instruction documents are intentionally ignored. They are not required for a fresh checkout to install dependencies or run the commands below. Some historical review documents reference those local files; use this README and checked-in source/evidence for public reproduction. Ignoring files removes them from the current tree, not earlier Git history.

## Architecture

### Implemented responsibility boundaries

React Native owns presentation and sends typed commands through a generated TurboModule. Kotlin and Swift own microphone capture, consent/privacy state, native lifecycle and generation/session/privacy epochs. The bridge exports validated operational metadata, not raw PCM, personal history or keys. Native state remains authoritative even when JavaScript detaches or reconnects.

Generic model assets have a separate installer boundary: manifest trust and license checks, bounded downloads into staging, streamed checksums, resumable checkpoints and atomic activation. Readiness fails closed when assets or native capabilities are unavailable. Generic model downloads are not permission to upload personal information.

Stop, lock, privacy changes and failed eligibility checks invalidate pending work. Late callbacks must not restart capture or publish stale results. Construction and background preference changes never automatically start recording.

### Planned conversation and service boundaries

```text
Explicit Start + consent + native readiness
                  │
                  ▼
Native microphone → bounded volatile buffer → wake/VAD → local streaming ASR
                                                             │
                                                             ▼
                 Protected eligible memory → bounded local prompt → local LLM
                                                                        │
                                                                        ▼
                                              Approved speech clauses → offline TTS

React Native UI ← validated state / released response presentation metadata

Optional account client → separate identity service → minimal auth/profile database
Confirmed search query  → separate search gateway → selected provider
```

Wake/VAD, ASR, LLM/TTS and personal memory integration in this diagram are planned responsibilities, not delivered behavior. Account and search services have not been provisioned. Personal transcripts, memory, raw audio, precise location and personal model state must not enter those services.

## Technology and compatibility

Versions below describe the checked-in project and recorded build environment, rather than recommendations to upgrade to the newest release. Install from lockfiles; review compatibility before changing dependencies.

| Component | Project baseline / responsibility |
| --- | --- |
| Node.js / npm | Node 24.11.1 and npm 11.6.2 used by the recorded local setup; hosted CI selects Node 24.11.1. `Eilo/package.json` declares npm 11.6.2. |
| React / React Native | React 19.2.3 / RN 0.87.1, New Architecture, Hermes and generated native interfaces. |
| Mobile tooling | React Native CLI 20.2.0. This is a native CLI project; Expo Go is not the run path. |
| TypeScript / JavaScript tests | TypeScript 6.0.3, ESLint 8.57.1, Prettier 2.8.8; Jest 29.7.0 for mobile and Vitest for shared contracts. |
| Navigation | React Navigation native 7.5.0, native-stack/bottom-tabs 7.20.0; screens 4.28.0 and safe-area-context 5.10.1. |
| Android | Kotlin 2.2.0, JDK 17, Gradle wrapper 9.4.1, compile SDK 37, target SDK 36, build tools 37.0.0, NDK 27.1.12297006; CI installs CMake 3.22.1. Minimum API 26 is a compiler/API boundary, not verified device performance support. |
| iOS | Full Xcode is required. Local setup records Xcode 27.0 / iOS Simulator 27.0; hosted validation uses `macos-26`. Swift package declares Swift tools 5.9 and iOS 18/macOS 13 minimums. Use the app's checked-in Podfile and lockfile for native dependencies. |
| Ruby / Pods | Use `apps/mobile/Gemfile.lock` and `Podfile.lock`; CI installs Bundler 4.0.16 and uses deployment-mode Pod installation. |
| Styling | React Native StyleSheet and shared semantic Design 2.0 tokens. |
| Planned inference | Native sherpa-onnx-compatible keyword spotting/VAD, Moonshine Small Streaming English ASR, Qwen3-1.7B GGUF Q4_K_M through in-process llama.cpp, installed offline platform English voices. These are evaluation directions, not integrated or benchmarked production components. |
| Planned personal storage | Native SQLCipher with device-protected keys; no personal storage in JavaScript. |
| Planned optional backend | Node/TypeScript, Better Auth and Neon PostgreSQL for minimal identity/profile data; Vercel is a hosting candidate. No live backend is implied. |

The workspace postinstall script applies a narrowly checked RN 0.87.1 Codegen path patch because the local project path contains spaces. It checks the expected source/version rather than silently modifying an unknown upstream release. CocoaPods links shared Swift source into the iOS app; the Swift package also tests that source without needing a phone.

## Local setup and running

Prerequisites: Git, the recorded Node/npm versions, and the platform toolchain. Android requires JDK 17 and the matching SDK/NDK/CMake components. iOS requires macOS, full Xcode with simulator components, Ruby/Bundler and CocoaPods dependencies. Standalone Apple Command Line Tools cannot build the iOS app.

```sh
git clone https://github.com/GemjuSherpa/Eilo.git
cd Eilo/Eilo
npm ci --no-audit --no-fund
```

The clone directory and inner workspace are both named `Eilo`; all following commands assume the inner directory containing `package.json`.

For iOS dependencies:

```sh
cd apps/mobile
bundle install
cd ios
bundle exec pod install --deployment
cd ../../..
```

Keep Metro running in one terminal:

```sh
npm start
```

In another terminal, from the inner workspace:

```sh
npm run ios -- --simulator="YOUR_INSTALLED_SIMULATOR_NAME"
# Or start an Android emulator / connect an Android phone, then:
npm run android
```

Find an installed iOS simulator with `xcrun simctl list devices available`. For an iPhone, open `apps/mobile/ios/Eilo.xcworkspace` in Xcode, select the Eilo scheme/device and configure your development signing team. Physical-device signing and store distribution are separate from the unsigned simulator checks below. Android requires `ANDROID_HOME` pointing to your SDK and `JAVA_HOME` pointing to JDK 17. Do not commit machine-specific paths, credentials or signing material.

## Reproducing validation results

From the inner workspace:

```sh
npm run lint
npm run typecheck
npm test
swift test --package-path packages/native-test-seam
```

Android compiler, native tests and lint:

```sh
cd apps/mobile/android
./gradlew :app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug --max-workers=2
# CI also builds debug and release test artifacts:
./gradlew :app:assembleDebug :app:assembleRelease --max-workers=2
cd ../../..
```

Unsigned simulator Release compilation, from the inner workspace:

```sh
xcodebuild \
  -workspace apps/mobile/ios/Eilo.xcworkspace \
  -scheme Eilo -configuration Release -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath apps/mobile/ios/build/Verification \
  CODE_SIGNING_ALLOWED=NO -jobs 3
```

For a local history secret scan with Gitleaks installed, from the repository root:

```sh
gitleaks git . --redact=100 --no-banner --log-level error --config .gitleaks.toml
git diff --check
```

At the VC-TURN-01 checkpoint (`e6307e3`, [PR #24](https://github.com/GemjuSherpa/Eilo/pull/24)), local Android compilation/lint and **74 JUnit tests**, **66 Swift tests**, iOS platform typechecking and unsigned simulator Release compilation passed. All **six hosted checks** passed across push and PR runs: JavaScript, Android and iOS/history. Hosted Android builds run native tests and debug/release compilation; Android lint is included in the recorded local checks. Counts can increase as subsequent tasks are implemented.

Fixtures use synthetic samples and injected clocks. They check bounded capacity, wrap order, oversized input, expiry, clock regression, stale callbacks and Stop cleanup. They do not validate microphone acoustics, wake quality, real model inference, device suspension or battery performance. See [S05 evidence](Eilo/docs/sprints/S05_REVIEW.md), [S04 evidence](Eilo/docs/sprints/S04_REVIEW.md), [device feasibility](Eilo/docs/sprints/S04_DEVICE_FEASIBILITY.md), [model installer contract](Eilo/docs/models/MANIFEST.md) and [distribution blockers](Eilo/docs/models/DISTRIBUTION_REVIEW.md).

## Development and review process

Work follows dependency-ready sprint tasks, using stable task IDs from the planning baseline. Each sprint has a branch such as `sprint/s05-turn-recognition`; each task has a separate branch such as `task/s05-vc-turn-02`.

1. Check task dependencies and define a small reviewable scope.
2. Implement and immediately run relevant compiler/lint checks and meaningful tests.
3. Record actual results and mark missing device/infrastructure checks explicitly.
4. Commit/push the task branch and merge it into the sprint branch.
5. Open or update a PR from the sprint branch to main and request review from Gemju Sherpa.
6. Merge to main only after approval; continue at the next review checkpoint.

Repository maintenance may follow an explicitly approved exception, such as this documentation/ignore cleanup pushed to main. Preserve unrelated work; do not force-push or rewrite history. Review approval is distinct from complete verification and deployment authorization.

Actions use pinned action revisions, read-only repository permissions and no signing/production secrets. Current jobs run only for a public repository and affected workspace/workflow paths. A skipped private-repository job is not a validation pass; private runner costs need separate review. Full native builds need more time than JavaScript checks.

## Constraints and outstanding gates

- Core conversation must work locally after verified assets are installed; no cloud inference fallback.
- Raw audio is volatile/native only. Personal conversations, derived memory, keys and precise location must not be uploaded or logged.
- Optional search needs confirmation of a minimized query per request. Account infrastructure stores minimal identity data only.
- Background listening requires independent consent and platform feasibility. Screen lock currently stops capture on both platforms; iOS background capability remains closed. Android's consented unlocked foreground-service path still needs physical verification.
- Model licenses, exact artifacts, native bindings, real performance and distribution trust are not established by build tests. Production readiness remains unavailable.
- No physical Android is available in the recorded test inventory. iPhone capture, routing, suspension, storage/backup and accessibility checks remain unverified. Simulator success does not substitute for them.
- Personal history encryption/key lifecycle, locked storage policy and real backup exclusion require their own native evidence before release.
- Existing dependency advisories and build/template warnings remain. This repository does not claim a clean security audit, compliance certification or release readiness.
- Development aims to avoid paid services. Use local tools and reviewed free-tier paths; do not provision services, deploy, sign/distribute store builds or incur charges merely to reproduce unit/simulator checks.

## Demo video

A walkthrough video will be added later. No completed voice-conversation demo is claimed at this checkpoint.
