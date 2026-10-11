# S05 / VC-TURN-02 — explicit Android Debug APK evaluation

11 October 2026. PR #38 reviewed/merged at verified main `c1dd847`. This partial VC-TURN-02 checkpoint awaits Gemju Sherpa review.

The prior loader had fixed names and a real host JNI version probe, but no APK packaging evidence. `check_android_package.py` now verifies existing pinned archives/extracted inputs, rebuilds the C/JNI wrapper for four ABIs and generates an ignored Debug-only Gradle init script. It stages only ONNX Runtime, sherpa-onnx C API and Eilo JNI. It preserves their symbols to verify exact staged bytes inside the APK, checks native dependencies, every 64-bit ELF LOAD alignment and SDK ZIP alignment. The previous Android checker shares its unchanged cross-link command through `build_android_jni`. No default project Gradle configuration, app caller, model trust or readiness changes.

The evaluation APK remains local/ignored. It contains no bundled models and does not execute the loader or microphone on Android. Structural ELF/ZIP checks follow [Android page-size guidance](https://developer.android.com/guide/practices/page-sizes); they do not prove operation on a 16 KB device. Default Debug/Release APKs are rebuilt after evaluation and inspected to contain zero wake-library entries. No download, tool installation, service, deployment or publication is performed.

## Actual checks

- Explicit Debug evaluation APK build PASS. All twelve expected wake-library entries across `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64` are uncompressed and match staged SHA256 values. Pinned vendor inputs verified before building. Unknown native dependencies rejected; all current dependencies resolve to the three included libraries or Android system libraries.
- All four JNI shared-library links PASS with NDK 27.1.12297006/API 26, warnings as errors and no undefined references. Every 64-bit LOAD alignment is at least 16 KB/power-of-two. SDK 37 `zipalign -c -P 16 4` PASS.
- Three focused Python tests PASS in normal and optimized modes: missing/invalid ELF alignment, missing dependency, missing/changed/compressed/extra/duplicate APK entries reject. Existing five integrity/report tests PASS in both modes. Python compilation PASS.
- Normal Android Kotlin compiler, lint, Debug/Release builds and 121 JUnit tests PASS; zero failures/errors/skips. Normal APK inspection confirms no wake libraries after restoration. No Kotlin behavior changed; existing host acoustic results are not rerun or reclassified.
- Same iPhone 18 Pro / iOS 27.0 simulator `E01AE333-A393-48F6-AAD7-579F0A5DB1F8`: normal Debug build PASS; three fresh ten-second launches verified before commit. Existing data/consent preserved; Swift code unchanged.
- Diff/secret checks: initial scanner flagged four library SHA256 values; a narrowly scoped field/path rule distinguishes these public artifact checksums from credentials. Final staged and checkpoint-commit scans PASS before sprint merge/publication.
- Physical Android execution/loader/AudioRecord/page-size/performance tests NOT RUN: no Android device/emulator. Production trust/model selection/licensing/default worker activation/vendor retention remain open. ASR remains gated.

Reproduction is documented in `Eilo/packages/wake-runtime/README.md`. Actual tracked report: `Eilo/packages/wake-runtime/tests/android-package-results.json`. Local logs: `/tmp/eilo-wake-package.log`, `/tmp/eilo-wake-package-normal-android.log`, `/tmp/eilo-wake-package-ios-build.log`, `/tmp/eilo-wake-package-ios-launch.log`. The generated APK is `Eilo/.local/kws/android/wake-evaluation-debug.apk`; do not distribute it as a production app.

Source control: `task/s05-vc-turn-02-android-packaging` → `sprint/s05-wake-android-packaging` → PR to main. Preserve unrelated S02 review edits. Stop for Gemju Sherpa review. Next checkpoint: Android native execution when a suitable device/emulator is available, and production trust/activation prerequisites; packaging does not complete VC-TURN-02.
