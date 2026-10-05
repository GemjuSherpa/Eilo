# S01 — Repository, board and build foundation

Branch: sprint/s01-foundation. State: awaiting human review; partial sprint verification. No staging, commits, pushes or merge performed. The owner reviews, commits and pushes. Do not start S02 without owner instruction.

## Results and stable task mapping

| Task | Implementation / scoped result | Verification |
|---|---|---|
| VC-BASE-01 / F13,A10 | Android guest shell: Eilo / Guest / Stopped; no capture, account or active controls. Main release manifest has no Internet or microphone permission; debug-only manifest grants Internet for Metro. | Debug/release compilation, emulator install/launch, screenshot, effective release permissions inspected. No physical Android available. |
| VC-BASE-02 / F13,A10 | Same guest shell on iOS, bundled Release simulator build, existing UIScene startup preserved. No microphone usage description or account entitlement added. | Release build/launch and screenshot pass without Metro. Three one-second nettop samples for the shell PID show no flow rows. This bounded observation is not a comprehensive privacy audit. Physical iPhone iOS26.6.1 not connected/tested. |
| VC-BASE-03 / F02,S04 | Versioned metadata-only state envelope in packages/contracts, fixed states/error codes, opaque UUIDv4 operation/session IDs, nonnegative safe-integer generation/privacy epoch. Exact keys; rejects personal fields, malformed values, symbols and accessors; returns an owned snapshot. | 25 Vitest cases pass. No bridge or native controller implementation claimed. |
| VC-BASE-04 / F13,S01 | Kotlin and Swift native dependency-injection seams for capture, ASR, model, TTS and memory; no concrete production adapters, files, networking or downloaded model dependencies. | Each native harness runs one synthetic successful turn and one ASR-failure case; downstream adapters stop on failure. Kotlin samples cleared on ASR completion/failure. Swift value-buffer reassignment is not a secure-zero guarantee. Production controller integration belongs to S02. |
| VC-VERIFY-01 / A12,N01–N08 | Premeasurement workload/sample-count/scoring/route protocol; available simulator and owner's iOS26.6.1 evidence declared. | PARTIAL: exact physical iPhone model/RAM, frozen fixture inventory/hashes and physical Android unavailable. Do not measure/report target passes yet. |
| VC-DEVOPS-01 / DP01 | Existing repository/project/sprint mapping preserved, previously reviewed by owner. Gitleaks added for history/current source verification. | History and source scans pass; narrow CocoaPods public checksum exception, generated dependencies/build caches excluded. No legal/privacy clearance or exhaustive archive audit claimed. |
| VC-DEVOPS-02 / DP02 | SHA-pinned Actions checkout/Node; affected foundation paths; JS lint/types/tests, Android debug/release/native tests, Swift XCTest, unsigned iOS Release compile and history scan. Read-only contents, checkout credentials not persisted, no signing/production secrets, deployments, caches or artifact uploads. Jobs restricted to public repo to avoid unreviewed private usage cost. | actionlint PASS; local corresponding commands PASS. Hosted trusted/fork PR execution and failed-check enforcement NOT RUN; owner must push and open a PR. No branch-protection enforcement claimed. Runner image differs from local Xcode27; first hosted run is a compatibility gate. |

## Actual checks

- npm run lint: PASS, source only (generated Gradle test report JavaScript excluded).
- npm run typecheck: PASS, strict TS in mobile/contracts.
- npm test: PASS, UI1 + contract25.
- Android: ./gradlew :app:assembleDebug :app:testDebugUnitTest --max-workers=4: PASS, two JUnit cases.
- Android: ./gradlew :app:assembleRelease --max-workers=4: PASS, locally template-debug-signed test APK. Initial failure to locate hoisted Hermes fixed via platform-placeholder hermesCommand path; no engine downgrade.
- Swift: swift test in packages/native-test-seam: PASS, two XCTest cases on this Mac. This package is a native test seam, not a mobile production controller.
- iOS: pod install + xcodebuild workspace Eilo / Release / iphonesimulator / generic destination / CODE_SIGNING_ALLOWED=NO: PASS. Simulator installed bundled app and visually rendered guest shell.
- Gitleaks8.30.1: git history and Eilo source scans PASS (redacted output). Initial generic-api-key finding was PODFILE CHECKSUM; exception matches only that 40hex public integrity-checksum line in Podfile.lock, no general credential exclusion.
- actionlint1.7.12: PASS. git diff --check: PASS.

Source dependency changes: removed the demo new-app-screen package; added design token/contract npm workspaces and Vitest5.0.3 (MIT, Node24 compatible). Reused official Design2.0 colors, no competing styling system. JUnit4.13.2 is native test-only. One npm lockfile retained. Shared contract package never stores personal values. No production controller/audio/inference/storage/auth behavior added.

Evidence: S01-ios.png, S01-android.png and DEVICE_WORKLOAD_MATRIX.md. Raw test/build diagnostics were temporary in /tmp/eilo-s01-*.log; screenshots contain only synthetic guest UI.

## Human verification

1. Inspect the diff and effective release manifest. Confirm no microphone/account permissions or startup adapter wiring.
2. From Eilo: npm ci, npm run lint, npm run typecheck, npm test. From packages/native-test-seam: swift test.
3. In apps/mobile/android with configured Java17/SDK: ./gradlew :app:assembleDebug :app:assembleRelease :app:testDebugUnitTest. Release APK is app/build/outputs/apk/release/app-release.apk and runs without Metro; debug requires npm start.
4. In apps/mobile/ios: bundle exec pod install, open Eilo.xcworkspace; run Release on simulator without Metro. Do not distribute debug/test-signed outputs.
5. Review the provisional device/workload matrix and supply the exact iPhone model/RAM; physical Android remains unavailable. Frozen dataset hash inventory must be accepted before performance measurements.
6. After owner commit/push, open a PR and verify all hosted checks (including trusted/fork restrictions and intentionally failed checks). Do not regard skipped private-repo jobs as successful validation. Keep workflows free of production secrets and do not proceed to another sprint until reviewed.

No compliance, native physical-device, audio, model performance, privacy-race, background or release-certification pass is claimed. S01's matrix and hosted-CI acceptance remain partial; those blockers are not silently marked complete.

Working-tree note: the tracked root .DS_Store changed during the session; preserved rather than reverted. It is not part of S01 implementation and should be excluded from the owner's commit.
