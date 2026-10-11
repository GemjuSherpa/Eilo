# S05 / VC-TURN-02 — Android packaged runtime execution

11 October 2026. Gemju Sherpa reviewed/merged PR #39 at verified main `ed0d3fc`. The small shared-harness adaptation and actual Android packaged-loader execution are combined into this partial VC-TURN-02 checkpoint. Awaiting review; ASR remains gated.

Previously the APK had structural checks but the runtime had executed only on macOS. The installed `Eilo_API35` ARM64 emulator is now started with audio disabled. `check_android_device.py` invokes the reviewed packaging verifier, adds an invocation-only Debug instrumentation manifest/runner/shared evaluator and pinned synthetic assets through an ignored Gradle init script, installs that APK and runs Android instrumentation. It accepts only an explicit emulator serial and verifies API35/ARM64/boot state. No image, dependency, service or microphone permission is installed/granted.

The shared evaluator preserves the reviewed direct/controller/queued synthetic acceptance and stale JNI handle assertions. The host wrapper remains an explicit macOS loader; the Android runner uses actual fixed-name `System.loadLibrary` and linked version probe. Model/fixture hashes are checked again after temporary app-private copying. Cleanup occurs before runner success; the verifier independently checks the temporary directory is gone, collects only the synthetic report and deletes that report. Android report validation requires the exact Android probe label; a host-only label rejects. No AudioRecord capture, JS PCM, personal recordings, production trust/profile or default app readiness is added.

## Actual evidence

- Android API35 / ARM64 emulator ART + packaged JNI PASS. All 28 frozen synthetic entries match direct/queued expectations: eleven wake, fifteen nonwake and two excluded diagnostics; 24 unique WAVs from one installed voice. Actual controller transitions, closed input/Stop rejection and invalid/stale JNI IDs PASS. Pinned model/fixture integrity and temporary asset cleanup PASS. Device page size is 4096 bytes; 16 KB execution NOT RUN.
- Invocation Debug packaging compilation, four ABI links, twelve library hashes, dependency/64-bit ELF/ZIP checks PASS. Three package rejection tests and five integrity/report tests PASS in both Python modes. Python compilation PASS.
- Extracted shared evaluator regression on real macOS host JNI PASS for all 28 cases; original strict case validation retained. Initial Android evaluation did not produce acceptance evidence; final compiled runner with cleanup before finish passes. No failed attempt is counted as passed.
- Normal Android compiler/lint, 121 JUnit tests and Debug/Release builds PASS after evaluations; normal APKs restored without wake libraries/assets/instrumentation. Normal Debug APK reinstalled on the same emulator.
- Same iPhone 18 Pro / iOS 27.0 simulator `E01AE333-A393-48F6-AAD7-579F0A5DB1F8`: normal Debug build and three fresh ten-second launches PASS before commit. Data/consent preserved. Swift unchanged.
- Staged diff/secret scan PASS; unrelated S02 review edits excluded.
- Physical Android AudioRecord/microphone/noise/route/performance/battery and 16 KB execution NOT RUN. Production model trust/selection/licensing/default activation and vendor retention remain open; VC-TURN-02 remains partial.

Reproduction: `Eilo/packages/wake-runtime/README.md` provides the explicit installed-emulator command and normal-build restoration steps. Actual tracked report: `Eilo/packages/wake-runtime/tests/android-device-results.json`. Local logs: `/tmp/eilo-wake-android-device.log`, `/tmp/eilo-wake-device-host-regression.log`, `/tmp/eilo-wake-device-normal-android.log`, `/tmp/eilo-wake-device-ios-build.log`, `/tmp/eilo-wake-device-ios-launch.log`. Evaluation manifest/assets and APK artifacts stay ignored.

Source control: `task/s05-vc-turn-02-android-execution` → `sprint/s05-wake-android-execution` → PR to main. Preserve unrelated S02 review edits. Stop for Gemju Sherpa review. Next production activation prerequisites and physical evidence remain separate; emulator acceptance does not close the whole wake/ASR dependency.
