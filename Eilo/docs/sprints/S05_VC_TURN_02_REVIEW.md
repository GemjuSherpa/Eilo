# VC-TURN-02 — native wake adapter boundary (partial)

Gemju Sherpa authorized this next task after reviewing VC-TURN-01. Branch: task/s05-vc-turn-02 → sprint/s05-turn-recognition → PR to main. Requirements F03/A02. VC-TURN-01 dependency is approved. This checkpoint does not finish the acoustic wake detector.

## Implemented boundary

Kotlin and Swift now provide a native keyword-stream adapter with explicitly validated phrase, threshold and boost configuration. Its backend port follows the keyword-only accept/decode/result/reset lifecycle described by [sherpa-onnx](https://k2-fsa.github.io/sherpa/onnx/kws/index.html); no vendor binary, native binding or model was installed. The test phrase HEY EILO and threshold/boost are synthetic fixture configuration, not a selected production phrase or measured threshold.

An independently verified backend and live native generation token are required to begin; defaults are unavailable. Backend construction receives the exact validated configuration. PCM16 is normalized into a fixed Float scratch buffer on Android; iOS accepts bounded finite normalized mono Float input at its actual sample rate. Each frame is limited to 100 ms at 8–192 kHz, with no queue or growing audio snapshot. Scratch storage is zeroed before return. Caller-owned audio remains the caller's responsibility; the capture adapters already erase their buffers.

The backend must consume borrowed samples synchronously on a serialized native inference worker, never retain the pointer/array, never call back into the adapter, implement verified sample-rate conversion when needed, and release its feature/stream state on close. Decode work is capped at 32 steps per frame; this is not a wall-clock latency guarantee. A future binding must validate those obligations against the actual runtime.

Only an exact configured keyword returns a metadata-only activation. Nonempty results are reset before the next frame, including unexpected keywords. Empty/ordinary/other results do not transition the controller. There is no conversational ASR/model/storage/network dependency in this adapter.

The controller checks detector lease validity under its serialization boundary and then uses its existing token/permission/model/state acceptance. Activation can transition standby to listening only; it does not endpoint a turn, invoke LLM inference or produce a reply. Stop/privacy changes revoke controller tokens. Detector close/rebind revokes its own lease, so queued detections cannot activate even when the controller token is otherwise unchanged. Backend errors and runaway decode close the adapter; a failed native close prevents reopening and produces allowlisted diagnostic metadata, not exception text or audio.

## Actual local evidence

- Android compileDebugKotlin, testDebugUnitTest and lintDebug: PASS. 84 tests, zero failures/errors/skips; ten new adapter tests.
- Swift XCTest: PASS. 76 tests, zero failures; ten new adapter tests.
- Common-source typecheck against the iOS Simulator SDK: PASS.
- Unsigned iOS simulator Release app compilation with the adapter included: PASS.
- Fixtures cover frozen keyword-result cases; normalization/erasure; invalid phrase/threshold/boost; invalid/oversized/nonfinite input; missing/revoked verification; backend open/decode/result/reset/close failures; bounded decode steps; Stop/privacy/permission races; close/rebind invalidation and restart without stale input poisoning a new stream.
- These are scripted keyword-engine contract fixtures. The frozen synthetic PCM is not an acoustic wake/nonwake dataset. No model call-count or recognition-accuracy result is claimed: conversational inference is structurally absent, and tests verify the controller never reaches thinking/speaking from these inputs.
- No dependency/lockfile or JS changes. Existing native build/template warnings remain. Hosted validation is recorded in the PR when available.

## Reproduce

From Eilo:

```sh
JAVA_HOME=/path/to/jdk17 ANDROID_HOME=/path/to/android-sdk \
  apps/mobile/android/gradlew -p apps/mobile/android \
  :app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug --max-workers=2
swift test --package-path packages/native-test-seam
xcodebuild -workspace apps/mobile/ios/Eilo.xcworkspace -scheme Eilo \
  -configuration Release -sdk iphonesimulator \
  -destination 'generic/platform=iOS Simulator' \
  -derivedDataPath apps/mobile/ios/build/Verification CODE_SIGNING_ALLOWED=NO -jobs 3
```

## Blockers and review boundary

Production KWS binding/version, checkpoint artifacts and license evidence, tokenized production keyword, calibrated threshold, verified resampling, runtime feature-buffer lifetime and bounded capture-to-worker delivery are not implemented/verified. The adapter is not wired to microphone capture. Production model readiness remains unavailable and no bypass was added. Real wake/nonwake fixtures, false activation/recognition scoring and phone measurements are NOT RUN.

Tracker: partial implementation, partial verification, awaiting review of this adapter boundary with production acceptance blocked. Do not mark VC-TURN-02 approved/complete from these fixtures, or advance VC-TURN-03 on a false dependency pass. Next work remains VC-TURN-02 runtime/checkpoint/capture integration after this review. Main merge awaits Gemju Sherpa review.
