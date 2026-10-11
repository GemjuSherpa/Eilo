# S05 / VC-TURN-02 — explicit Android native runtime loader

11 October 2026. PR #37 is reviewed/merged at verified base main `b7f4dc8`. This partial VC-TURN-02 checkpoint awaits Gemju Sherpa review.

`NativeWakeRuntime` now explicitly loads the fixed packaged names `onnxruntime`, `sherpa-onnx-c-api`, then `eilo_wake_jni`. A JNI probe checks the linked sherpa-onnx C API version is exactly 1.13.8 before returning the API. Construction performs no loading; each instance caches success or failure. Partial linker failures, exceptions and missing/incompatible probes fail closed without retry. Invoke on the separate inference worker before signed-pack setup. Packaging/system linker is the native code-trust boundary; the version probe alone does not authenticate library bytes.

The evaluation harness uses the same loader with a pinned macOS absolute-path loading shim, then the actual JNI version probe and all 28 frozen direct/queued synthetic cases. The report verifier rejects missing or incorrect host-only loader evidence labels. The shim is evaluation-only; the default loader accepts fixed packaged names.

No APK libraries, default app caller, production model selection/trust, readiness or microphone consent are added. ASR remains gated. Actual Android execution, library packaging/page-size compatibility, production trust/licensing and physical microphone/route/noise/latency/vendor-buffer-retention evidence remain open.

## Actual validation

- Android Kotlin compilation, lint, Debug/Release builds and 121 normal JVM tests PASS, zero failures/errors/skips. Three new tests cover fixed load ordering, construction without loading, cached success/failure, partial failures and incompatible/missing/throwing probes.
- Real pinned sherpa-onnx 1.13.8 macOS host JNI probe and all 28 synthetic direct/queued cases PASS. Eleven wake entries, fifteen nonwake entries, two excluded diagnostics, 24 unique WAVs from one installed voice. All four Android ABI shared-library links PASS. This is host JVM execution, not Android execution.
- Five report/integrity tests PASS in normal Python and optimized Python modes.
- Same iPhone 18 Pro / iOS 27.0 simulator `E01AE333-A393-48F6-AAD7-579F0A5DB1F8`: normal Debug build and three fresh ten-second launches PASS. Existing simulator data/consent preserved; Swift acoustic evaluation not rerun for this Android checkpoint.
- Read-only Git diff whitespace check PASS. Unrelated `S02_REVIEW.md` edits preserved. Scoped Git publication is authorized by Gemju Sherpa; task changes follow the task-to-sprint-to-main PR workflow.

Reproduce from repository root with the installed cached tools:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
ANDROID_HOME=/Users/gemju/Library/Android/sdk \
Eilo/apps/mobile/android/gradlew -p Eilo/apps/mobile/android \
  :app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug \
  :app:assembleDebug :app:assembleRelease --offline --max-workers=2
python3 Eilo/packages/wake-runtime/check_android.py \
  --ndk /Users/gemju/Library/Android/sdk/ndk/27.1.12297006 \
  --java-home /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
  --android-sdk /Users/gemju/Library/Android/sdk
python3 Eilo/packages/wake-runtime/test_android_integrity.py
python3 -O Eilo/packages/wake-runtime/test_android_integrity.py
```

After the standalone evaluation, rerun normal Gradle tests to restore the normal suite results. iOS launch command: `python3 -O Eilo/scripts/verify-ios-launch.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8 --dwell 10`, after building/installing the normal Debug workspace app. Actual tracked JNI evidence: `Eilo/packages/wake-runtime/tests/android-results.json`. Local logs: `/tmp/eilo-wake-loader-jni.log`, `/tmp/eilo-wake-loader-final-android.log`, `/tmp/eilo-wake-loader-ios-build.log`, `/tmp/eilo-wake-loader-ios-launch.log`.

Current task branch: `task/s05-vc-turn-02-runtime-loader`; sprint branch: `sprint/s05-wake-runtime-loader`. Commit/push the task, merge into the sprint branch and open its PR to main for Gemju Sherpa review. Next checkpoint: Android runtime packaging; production trust/default activation and physical gates remain before completing VC-TURN-02. Stop for review.
