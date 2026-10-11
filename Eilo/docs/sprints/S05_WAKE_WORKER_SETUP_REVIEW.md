# S05 / VC-TURN-02 — signed wake-pack worker construction and attachment

11 October 2026. Gemju Sherpa reviewed/merged PR #36; fetched and verified base main `ee928f8`. This partial VC-TURN-02 checkpoint (F03/A02) awaits review; ASR/VC-TURN-03 remains gated.

Previously capture attachment and signed pack selection were separate native APIs, with no operation that owned construction and failure cleanup. `WakeCaptureInstaller.install` now resolves the signed store lease, constructs its native stream/detector/delivery, and attaches to capture under a setup ticket. The ticket must be minted before scheduling construction on a separate native inference worker. Do not enqueue construction behind the capture executor's continuous read loop. This synchronous operation does not create executors, auto-install models, load a library or enable app readiness.

The ticket binds capture identity, controller, generation, capture run and context epoch. It requires an eligible open standby capture before issuance, is rechecked before/after pack resolution and at final attachment, and is consumed by successful attachment. Stop, context clear/cancel and capture replacement invalidate a late setup. Closed delivery cannot attach. A competing/stale/failed candidate remains installer-owned and closes without disturbing a successfully attached binding. On successful attachment, capture owns delivery; its stream wrapper revokes the pack lease when closing the native stream. Model verification is still checked by the decoder and when applying metadata as reviewed in PR #36.

The signed snapshot validates signatures, configured trust/runtime, license evidence and file hashes; model selection retains exact native configured IDs/hashes/roles/extensions. Resolution remains worker-side. Borrow/application checks use disk-free leases. App-private slots must remain immutable; this is not continuous external-tamper detection. There is no default app caller or production key/profile, download, JNI library packaging/loading or model-ready bypass. Missing/corrupt pack or unavailable default API returns failure without attachment; existing capture remains under its controller lifecycle. Runtime loader/packaging, production trust/licensing and physical microphone/route/noise/latency/vendor-retention gates remain open before ASR.

## Actual validation before commit

- Android compiler/lint and Debug/Release builds PASS with installed JDK 17/SDK and cached dependencies.
- 118 normal JUnit tests PASS: zero failures/errors/skips. Five added tests use synthetic signed four-byte assets, the actual signed store and real capture/inference Java executors with a scripted native API. They cover successful worker construction and capture feeding; context cleanup before queued setup; Stop/context cleanup during blocked opening; fresh setup after rejection; missing/corrupt pack/unavailable runtime; closed delivery and consumed-ticket rejection; stream cleanup on generation/lifecycle end. Native creation is asserted on the separate inference worker.
- Same iPhone 18 Pro / iOS 27.0 simulator `E01AE333-A393-48F6-AAD7-579F0A5DB1F8`: normal Debug build and three fresh ten-second launches PASS. Simulator data/consent preserved. Swift code unchanged; Swift/JNI acoustic evaluations not rerun for this Android construction checkpoint.
- Staged diff check and staged Gitleaks secret scan PASS; unrelated S02 edits excluded.
- Physical Android AudioRecord/microphone/device/route/timing tests NOT RUN (no Android device). Scripted model/capture data is not a real acoustic or physical pass. Existing reviewed synthetic acoustic reports remain unchanged.

Reproduce Android from repository root:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
ANDROID_HOME=/Users/gemju/Library/Android/sdk \
Eilo/apps/mobile/android/gradlew -p Eilo/apps/mobile/android \
  :app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug \
  :app:assembleDebug :app:assembleRelease --offline --max-workers=2
```

Build/install normal Eilo iOS workspace/scheme Debug for that already-booted simulator, then run `python3 -O Eilo/scripts/verify-ios-launch.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8 --dwell 10`. Local temporary evidence: `/tmp/eilo-wake-worker-compile.log`, `/tmp/eilo-wake-worker-final.log`, `/tmp/eilo-wake-worker-ios-build.log`, `/tmp/eilo-wake-worker-ios-launch.log`.

Source control: `task/s05-vc-turn-02-wake-worker-setup` → `sprint/s05-wake-worker-setup` → PR to main. Unrelated S02 review edits excluded. Stop for Gemju Sherpa review. Next checkpoint: verified native runtime packaging/loading; production trust and physical gates remain explicit.
