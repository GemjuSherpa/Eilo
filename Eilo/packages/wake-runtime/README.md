# Native keyword runtime evaluation

VC-TURN-02 evaluation checkpoint. Gemju Sherpa selected **Hey, Eilo**, pronounced **Ay-loh**, including a natural pause after Hey. The selected phonetic sequence is `HEY A LOW`, with eight active paths, one trailing blank, threshold **0.125** and boost **1.5**. The expanded local synthetic acceptance set passes: all eleven wake entries detected, all fifteen nonwake entries inactive. Two diagnostic controls are excluded from acceptance. These are 28 entries / 24 unique waveforms from one installed voice; mobile integration and physical calibration remain open.

The C++ wrapper calls the real sherpa-onnx 1.13.8 C API with the GigaSpeech 3.3M Zipformer checkpoint. It accepts synchronous borrowed mono Float frames up to 100 ms, validates finite normalized samples and a stable 8–192 kHz rate, caps decode at 32 steps, reads and resets results after each decode, and returns only the fixed `HEY_EILO` label. Input errors permanently disable that handle; the caller must destroy it. No ASR transcript, conversational model, file sink, microphone or network API is present in the wrapper. This does not attest to vendor buffer erasure, bounded feature retention, fatal-abort recovery or mobile performance.

`provenance.json` freezes archive hashes and the actual extracted files used. The runtime archive hash matches the publisher's release-asset digest. The model hash was observed locally from the official HTTPS release; its release metadata provides no publisher digest. That distinction remains a production trust gate. The archived model card declares Apache License 2.0; exact distribution rights and transitive model/runtime dependencies still need review. Model weights, vendor libraries and generated system-voice audio remain local and outside the public Git index. System-voice redistribution rights have not been established, so only fixture metadata/results are published.

## Reproduce on macOS ARM64

Use installed Python 3.11+ and Xcode command-line tools. No Python package installation is needed. From `Eilo`, download the two exact URLs in `provenance.json` to `.local/kws/runtime.tar.bz2` and `.local/kws/model.tar.bz2`, verify their listed SHA256 hashes, and extract them under `.local/kws`. The extracted directory names must match the manifest. The locally frozen WAVs live in `.local/kws/fixtures`; their hashes and synthetic source text are recorded in the committed manifest. A fresh checkout can run `python3 packages/wake-runtime/generate_fixtures.py` using the same installed Samantha voice/tool output. Each say/afconvert command is bounded to 30 seconds. A subsequent full regeneration stalled in the installed voice on an existing ordinary-speech phrase and was stopped; full regeneration is not claimed as passing for this correction. The scored frozen files still pass integrity checks. It checks every generated hash against the frozen manifest and fails on empty or changed output without changing expected hashes. Exact reproduction across different OS/voice versions is not claimed. Audio is not downloaded or distributed by this project. Then run:

```sh
python3 packages/wake-runtime/check_host.py
```

The script first rejects empty/one-sided acceptance sets, unknown fixture classifications, duplicate filenames, escaping paths and malformed digests; then verifies archives, extracted header/libraries/model files and frozen fixture hashes before compiling. It builds with C++17 and `-Wall -Wextra -Werror`, runs scripted C ABI contract tests with AddressSanitizer and UndefinedBehaviorSanitizer, then scores all frozen WAVs using the real CPU decoder. It does not use a microphone, fetch files, install packages or enable model readiness. The report is written to ignored `.local/kws/host-results.json`. A format/energy gate rejects empty or silent fixtures before scoring; run its eight regression tests with `python3 -m unittest discover -s packages/wake-runtime -p test_fixture_validation.py`. The initial sandbox-generated silent files and their invalid scores were discarded and regenerated with the installed voice before freezing these artifacts.

Exit 0 means this limited synthetic acoustic set passes; exit 1 means acoustic acceptance failed; exit 2 means checks could not run. **The current expected outcome is exit 0 on the frozen synthetic set**, with compiler/contract checks passing. This does not establish physical-phone or shipped app recognition. The committed `tests/results.json` records the actual run.

Local fixtures are frozen macOS Samantha TTS outputs, 16 kHz mono PCM16 with one second of zero padding at each end. Their source text and hashes are in `tests/fixtures/manifest.json`. Eleven intended target variants, fifteen nonwake cases and two exploratory pronunciation/spelling controls are retained. The eight comma-pause/near-miss additions were generated after selecting the corrected configuration. The diagnostic controls are not scored as wake/nonwake acceptance. One diagnostic is detected; that does not validate the requested pronunciation. The report exposes 28 fixture entries and 24 unique waveform hashes. Some TTS spelling variants yield identical waveform hashes, so case counts are not independent speaker samples. There is no held-out speaker/noise dataset, calibrated error rate, measured phone accuracy or real-user audio.

The temporary exploration used threshold/boost pairs `(0.25,1.5)`, `(0.25,3)`, `(0.1,3)`, `(0.1,5)`, `(0.05,5)`. These runs used the earlier `HEY A LOW` lexicon: the default pair detected two of five target variants; threshold 0.1/boost 3 detected four of five; other pairs detected none. All five nonwake fixtures yielded zero detections. The previous `HEY ALO` candidate at 0.1/3 detected five of seven intended targets but also activated on the added nonwake phrase `Hello Ailo`. The eight additional phrases were generated after selecting the final lexicon/parameters, but use the same TTS voice. These are limited tuning/validation observations, not representative accuracy evidence. Production thresholds remain undecided. The subsequent correction uses `HEY A LOW`, eight paths, threshold 0.125 and boost 1.5. Controlled ablations on the failing samples show that restoring four paths misses the paused target, restoring boost 3 reintroduces both misses and the Hello false activation, and restoring the old lexicon activates on Hey alone. [Tuning evidence](tests/acoustic-tuning-results.json) preserves the failed baseline, explicitly partial searches and full original-set selection results. [Current results](tests/results.json) record the unchanged original fixtures plus additional comma-pause validation; no failed original sample was removed or relabeled.

The iOS Swift/C ABI binding and bounded native delivery are evaluated on the simulator. The Android Kotlin/JNI binding is now cross-linked for all ABIs and evaluated with the real decoder on the host JVM. Android runtime packaging/capture delivery, production model-pack trust/attachment and physical calibration remain outstanding. Mobile dependency lockfiles and default model readiness remain unchanged. Complete the integration gate before VC-TURN-03.

## iOS binding evaluation

`NativeWakeStream.swift` owns a single opaque C handle, maps only the fixed keyword to `HEY EILO`, borrows frames synchronously and closes on invalid input, changed sample rate, native errors or revoked verification. Result reads/reset and idempotent close share a native lock. C++ owns the actual decoder/reset. Opening requires an independent verification callback before and after creation; linking alone grants no model readiness. The real implementation requires `DEBUG`, `EILO_WAKE_EVALUATION` and the `CEiloWake` module. Standard Debug/Release builds fail closed without these conditions. This binding does not select a model pack, request permission or start capture.

The exact iOS static XCFrameworks are sherpa-onnx **1.13.8** and its declared ONNX Runtime **1.28.2** dependency. [iOS provenance](ios-provenance.json) records the publishers' Swift package URLs/checksums and locally observed extracted hashes. The local C wrapper compiles for iOS 18 device and ARM64 simulator; actual decoding is measured only on the iPhone 18 Pro / iOS 27.0 simulator. Deployment compatibility is separate from physical device support. The binaries, model weights and synthetic voice WAVs stay under ignored `.local/kws`; this does not authorize redistribution or store release.

From `Eilo`, download the two archive URLs in `ios-provenance.json` to `.local/kws/ios/sherpa-ios-static.zip` and `.local/kws/ios/onnxruntime-ios-static.zip`. Verify their exact listed SHA256 checksums before extracting both into `.local/kws/ios`. Use the existing verified model archive/files and frozen WAVs described above. Then run, with your explicitly selected booted simulator UDID:

```sh
python3 packages/wake-runtime/check_ios.py --udid YOUR_BOOTED_SIMULATOR_UDID
python3 packages/wake-runtime/test_ios_integrity.py
python3 -O packages/wake-runtime/test_ios_integrity.py
```

The verifier checks archives, all recorded extracted runtime files, models and WAVs before compilation/execution. It compiles the C wrapper for both iOS slices and the Swift binding/synthetic runner for ARM64 simulator, then scores all 28 entries via `simctl spawn`. Each spawned process consumes one verified synthetic file, never a microphone; it also confirms input rejection after close. Commands have deadlines. Reports are written to `.local/kws/ios/ios-results.json`; [recorded results](tests/ios-results.json) show eleven wake detections and no activations on fifteen nonwake entries. Two diagnostics are excluded, and the 28 entries represent 24 unique WAVs from one installed voice. These results do not establish physical accuracy, real route handling, vendor buffer erasure or full ASR integration.

A successful compilation generates `.local/kws/ios/WakeEvaluation.xcconfig`. Use it only for a **local ARM64 simulator Debug** build:

```sh
xcodebuild -workspace apps/mobile/ios/Eilo.xcworkspace -scheme Eilo \
  -configuration Debug -sdk iphonesimulator \
  -destination 'id=YOUR_BOOTED_SIMULATOR_UDID' \
  -xcconfig .local/kws/ios/WakeEvaluation.xcconfig \
  -derivedDataPath apps/mobile/ios/build/SimulatorDiagnosis \
  CODE_SIGNING_ALLOWED=NO -jobs 3
```

The configuration links local static libraries and adds the Debug-only Swift import/flag plus an iOS 18 deployment floor. It does not bundle models or turn on app wake recognition. Omit `-xcconfig` to build the normal app without vendor dependencies. No network download, install, device creation/erase or model-readiness change occurs in the verifier; missing/tampered assets or runner failures return exit 2, and failed acoustic acceptance returns exit 1.

## Native iOS capture delivery

`WakeFrameDelivery` preallocates four mono Float frame slots and one worker scratch frame. Each callback frame is limited to 100 ms at its fixed 8–192 kHz rate; queued frames must be younger than 250 ms when submitted/drained. The audio callback copies only. It never calls the decoder, controller or dispatches per-frame work. Overflow, invalid samples, rate changes or clock/age discontinuities erase queued data, revoke pending activation and cause one worker failure report. Frames are not silently dropped into an existing streaming decoder.

`IOSCaptureEffects` creates a per-capture slot, submits the first input channel before erasing the callback buffer, and drains on its native 50 ms worker timer. Native `connectWakeDetector` attaches an exclusively owned, independently verified detector/current generation after capture startup. That method is not on the JS bridge and is not called by the default app while model readiness is missing. Decoder results reach the controller only after the worker borrow/locks end; detector and delivery leases are rechecked inside the controller. Stop closes the slot, revokes events, clears queued samples and waits for any synchronous decode to finish before erasing scratch/destroying the stream. Generation cancellation detaches delivery without reopening capture; a fresh verified detector/token can be attached. This does not prove a physical Stop-latency target or vendor-owned feature-buffer erasure.

The same offline `check_ios.py` now scores every fixture both directly through the real C binding and through this queue/controller path. It uses a deterministic synthetic receive clock, batches three 20 ms frames before draining, checks the expected controller transition, then verifies Stop rejects pending events/input. `delivery_detections` must match the direct decoder for all entries. This is native transport evidence from synthetic files, not a real microphone/timing/device-route test. Android binding and production model-pack trust/lifetime remain required before ASR integration.

## Android Kotlin/JNI binding evaluation

`NativeWakeStream.kt` now adapts the same C ABI through a narrow native-only JNI object. The default API remains unavailable; neither the app nor this object automatically loads a library, installs models or opens capture. Opening requires independently verified native paths and verification before/after creation. Keyword reads latch only `HEY EILO`; C++ owns decoding/reset. Invalid bounds/samples, rate changes, native errors or revoked verification clear the result and close the handle. Explicit close is serialized with a synchronous borrow and is idempotent; callers must close their exclusively owned stream. Verification callbacks must not acquire controller/capture locks.

JNI uses monotonically increasing opaque IDs rather than exposing pointers. Lookup, processing and destruction serialize under one native mutex. Each stream owns a fixed 19,200-Float scratch array; `GetFloatArrayRegion` copies only the bounded prefix, consumes it synchronously, then erases that owned copy through volatile stores. Invalid input destroys the session, and closed/stale IDs cannot address a later stream. JNI does not retain Java arrays or export PCM/results to JS. This is a native worker API, not an audio callback API. Vendor internal retention/erasure and physical Stop latency remain unverified.

The [Android provenance](android-provenance.json) pins the official sherpa-onnx **1.13.8** Android archive with its publisher release-asset SHA256 and every extracted file used. Download its exact URL to `.local/kws/android/runtime.tar.bz2`, check the recorded archive digest, and extract its `jniLibs` under `.local/kws/android`. Use the previously pinned host runtime/header, model and frozen synthetic WAVs described above. No binary/model/audio file is added to the app or public repository. Production trust, transitive licensing and distribution remain gates.

On macOS ARM64 with the project's installed Android SDK, NDK **27.1.12297006**, a full **JDK 17** including JNI headers and cached Gradle dependencies, run from `Eilo`:

```sh
python3 packages/wake-runtime/check_android.py \
  --ndk /absolute/path/to/android-sdk/ndk/27.1.12297006 \
  --java-home /absolute/path/to/jdk17/Contents/Home \
  --android-sdk /absolute/path/to/android-sdk
python3 packages/wake-runtime/test_android_integrity.py
python3 -O packages/wake-runtime/test_android_integrity.py
```

This offline verifier rejects changed archives, extracted libraries/header/models and WAVs before compiling. It cross-links the C wrapper/JNI with warnings as errors and no undefined references for API 26 `arm64-v8a`, `armeabi-v7a`, `x86` and `x86_64`. It then builds a macOS host JNI library and temporarily adds the standalone evaluation test source through an ignored Gradle init script. That explicit host-JVM test uses the actual app Kotlin binding, detector and controller with synthetic capture/readiness fixtures. It scores all 28 frozen entries, verifies controller transitions/Stop and invalid/stale JNI IDs. The report must cover every expected file/classification and closed-input/Stop checks; a passing label cannot hide a missing or failed case. Exit 0 means this evaluation passed; exit 2 means integrity/compiler/runner/acceptance checks failed. The verifier does not download, install, provision, enable production readiness or use a microphone.

[Recorded Android binding results](tests/android-results.json): eleven wake entries detected, zero activations on fifteen nonwake entries, two excluded diagnostics; 24 unique WAVs from one installed voice. Four Android ABI links passed, but decoder execution was on **macOS JVM**, not an Android device/emulator. Normal Android Debug/Release builds and 93 JVM unit tests/lint pass independently without packaging the evaluation library. Actual Android runtime packaging/loading, bounded capture-to-worker delivery, verified production pack attachment, microphone/route/latency and vendor buffer retention remain open before ASR. Physical tests and native library page-size/device compatibility are not established by cross-linking.
