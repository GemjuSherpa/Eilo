# S05 / VC-TURN-02 — queued wake verification revocation

11 October 2026. Gemju Sherpa reviewed/merged PR #35; fetched and verified main `40f0870`. This corrective checkpoint remains part of VC-TURN-02 (F03/A02), awaiting review. ASR/VC-TURN-03 remains gated.

A wake event produced while model verification was valid could previously activate after verification was revoked between decoding and event application. Controller checks covered the generation and detector/delivery leases, but did not recheck model verification at that boundary. The new Android regression test fails against the previous implementation with an assertion on accepted activation.

Android and iOS `WakeActivation` now carry the detector's native verification callback and recheck it inside the controller's state-transition monitor after detector/delivery leases pass. A failed check permanently revokes the detector lease; later restoration of verification cannot revive that event or the old decoder generation. Android verification exceptions fail closed. The next worker input detects the revoked lease and closes without another backend call. Applying metadata does not acquire the decoder/capture lock or destroy a stream under the controller monitor. Caller-owned delivery/decoder cleanup remains required.

Verification callbacks must be disk-free, nonblocking native lease checks and must not acquire controller/capture/decoder locks. Android `WakePackLease.verified()` meets this contract. Expensive signature/hash work remains worker-side resolution, not event application. This is a point-in-time verification check, not synchronization of arbitrary file mutation or a substitute for immutable app-private pack slots and orderly revocation/cleanup. No microphone, JS PCM, model download, runtime loader, trust key or readiness bypass is introduced.

## Actual validation before commit

- Negative control: one new Kotlin regression test on the previous detector FAILED as expected (`verificationRevokedAfterDecodeRejectsQueuedEventPermanently`), demonstrating the gap.
- Android compiler/lint, Debug/Release builds and 113 normal JUnit tests PASS; zero failures/errors/skips. Two added tests cover false/throwing verification after decoding, irreversible event rejection, no additional backend input, and actual signed-store replacement after draining the native queue.
- `swift test --package-path Eilo/packages/native-test-seam` PASS: 95 XCTest tests. Two added tests cover post-decode revocation and post-drain revocation with permanent rejection and cleanup on next worker input.
- Same iPhone 18 Pro / iOS 27.0 simulator `E01AE333-A393-48F6-AAD7-579F0A5DB1F8`: normal Debug app build and three fresh ten-second launches PASS. Consent/device data preserved.
- Staged diff check and Gitleaks secret scan PASS; unrelated S02 changes excluded.
- Acoustic/JNI fixture evaluations NOT RERUN: decoder/configuration/model assets are unchanged. Existing reviewed synthetic recognition evidence is retained; these new tests use scripted native engines and synthetic signed assets.
- Physical Android/iPhone microphone, route/noise/latency and vendor retention checks NOT RUN. Production runtime/pack trust/worker attachment and physical gates remain open. VC-TURN-02 remains partial, and ASR is unavailable.

Reproduce Android from repository root with installed JDK 17/SDK and cached dependencies:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
ANDROID_HOME=/Users/gemju/Library/Android/sdk \
Eilo/apps/mobile/android/gradlew -p Eilo/apps/mobile/android \
  :app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug \
  :app:assembleDebug :app:assembleRelease --offline --max-workers=2
swift test --package-path Eilo/packages/native-test-seam
```

Build/install the normal Eilo iOS workspace/scheme Debug app on the already-booted simulator, then run `python3 -O Eilo/scripts/verify-ios-launch.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8 --dwell 10`. Local temporary logs: `/tmp/eilo-wake-revocation-negative.log`, `/tmp/eilo-wake-revocation-android.log`, `/tmp/eilo-wake-revocation-swift.log`, `/tmp/eilo-wake-revocation-ios-build.log`, `/tmp/eilo-wake-revocation-ios-launch.log`.

Source control: `task/s05-vc-turn-02-wake-revocation` → `sprint/s05-wake-revocation` → review PR to main. Unrelated S02 review edits preserved/excluded. Stop for Gemju Sherpa review; subsequent runtime attachment remains a separate checkpoint.
