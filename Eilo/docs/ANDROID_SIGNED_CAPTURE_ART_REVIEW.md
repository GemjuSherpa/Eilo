# Android signed capture evaluation on ART

The Android API 35 ARM64 emulator now runs the signed VAD/ASR installer against real JNI libraries. This closes the prior host-JNI-only execution gap; it does not enable the ordinary app pipeline.

## Change and provenance

The existing Moonshine library requires ORT symbols at version 1.23.2. The cached Sherpa ORT 1.28.2 cannot satisfy that requirement. Five MIT-licensed Microsoft headers, pinned to commit a83fc4d58cb48eb68890dd689f94f28288cf2278 (670,404 bytes total), were obtained within the approved header-only scope. No new runtime, model, package or service was downloaded.

The unchanged cached Moonshine Android ORT 1.23.2 runtime rejects ONNX input. The approved Silero source model was converted locally into ORT format using the cached host ORT 1.23.0 runtime with graph optimization disabled. The converter source, original model digest, converted model digest, runtime binaries and APK digests are recorded. No vendor binary, API version macro or symbol was patched. Earlier failed attempts remain in ignored local evidence directories.

Swift and Kotlin admit exactly `silero_vad_v5.ort` for the VAD role. Signed manifest, file size, digest, license evidence and revocation checks still apply. Other ORT VAD names and wrong roles are rejected.

## Evaluation

The explicit emulator-only runner uses an invocation-only Debug source set. It removes both Internet and microphone manifest permissions, verifies packaged native bytes, feeds the frozen synthetic waveform from private files, removes its files, and restores the normal APK. Model files, headers, runtime binaries, audio and raw logs are not committed. Reports retain counts and transcript hashes.

All eight real ART cases passed: 16 kHz speech, resampled fixture at 48 kHz, quiet, Stop during finalization, pack replacement during finalization, idle Stop, stale setup ticket, and corrupt pack. Case results match the host-JNI report. Controller permission and model readiness are synthetic. This is no evidence of microphone capture, calibrated ASR confidence, Android LLM/TTS integration, acoustic quality, network behavior or physical acceptance.

The normal suite passed 380 Android tests, lintDebug, assembleDebug and compileReleaseKotlin. Swift passed 325 tests; the normal iOS simulator app built, installed and survived three fresh launches. Workspace lint/types and 58 mobile, 33 contract and 27 search tests passed. The existing signed installer simulator/host-JNI and joined simulator VAD/ASR → LLM → speech SDK evaluations were rerun with the modified sources. Evidence validators and their adversarial tests pass with and without Python optimization.

GitHub must pass all applicable checks on the final PR head before merge. S08/release remains HOLD; persistent memory remains disabled; physical and network gates remain NOT_RUN.
