# Native streaming ASR evaluation

Moonshine Small Streaming English (v0.1.5, quantized model2026-08-21, C API30000) runs in process on a native worker. Eilo's wrapper bounds one turn to30 seconds and output to4096 UTF-8 bytes. It excludes vendor microphone, downloads, networking, speaker identification, contextual bias and text diagnostics. A canceled generation or revoked model lease cannot release a final transcript. Native PCM/text scratch is cleared after borrowed calls; the vendor's internal allocator erasure remains unverified.

The normal app still requires verified production packs and the remaining conversation models. Evaluation code does not grant readiness, microphone permission, distribution approval or physical performance evidence.

The [official v0.1.5 Swift package](https://github.com/moonshine-ai/moonshine-swift/blob/v0.1.5/Package.swift) supplies the matching XCFramework. The older manifest in the main source repository points to an unavailable v0.0.8 archive; do not use it. Android native libraries come from [Maven Central v0.1.5](https://repo.maven.apache.org/maven2/ai/moonshine/moonshine-voice/0.1.5/). Only C/C++ libraries are extracted; the Java SDK's microphone and automatic downloader are omitted. Moonshine source/English models are MIT according to the [publisher](https://github.com/moonshine-ai/moonshine/tree/v0.1.5); the full bundled third-party notice inventory remains a distribution gate.

Run from the Eilo workspace on this Mac, with Xcode and NDK27.1.12297006 available:

```sh
python3 packages/asr-runtime/fetch_assets.py --with-ios --with-android --generate-fixtures
python3 packages/asr-runtime/check_host.py
python3 packages/asr-runtime/check_ios.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8
python3 packages/asr-runtime/check_android.py \
  --ndk /Users/gemju/Library/Android/sdk/ndk/27.1.12297006 \
  --java-home /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
  --android-sdk /Users/gemju/Library/Android/sdk --serial emulator-5554
```

Downloads and generated system-voice audio remain in ignored `.local/asr`. Publisher sizes/CRC32C protect the model's catalog artifacts; the recorded SHA256 values are local digests computed after that verification. Runtime archive SHA256 values are publisher checksums. Each evaluation checks pinned archives, extracted libraries, model files and synthetic WAV hashes before use. Different installed voice output fails fixture validation instead of rewriting the frozen set.

Android evaluation registers invocation-only Debug instrumentation, temporarily packages models/libraries, checks real ART/JNI decoding and stale-final rejection, deletes temporary app files, then completes a normal Debug rebuild and restores that APK without clearing app data. Android vendor ABIs are arm64-v8a, armeabi-v7a and x86_64; x86 is unavailable. iOS compiles the wrapper for physical ARM64 and executes the real Swift binding in the selected simulator. A device compiler pass is distinct from physical execution. The recorded reports are synthetic-only; no microphone trial, accent diversity or physical quality pass is inferred.

## Relocatable iOS framework evaluation

`framework.py` creates a local two-slice ARM64 `CEiloAsr.xcframework` from approved caches and runs a relocated simulator client with the current ASR adapter and linked unloaded LLM. See [S07 review](../../docs/sprints/S07_ASR_FRAMEWORK_REVIEW.md). It downloads nothing and enables no normal-app runtime. Device signing/execution/distribution and full conversation acceptance remain open.

```sh
python3 packages/asr-runtime/framework.py --asr-cache "$ASR_CACHE" --llm-cache "$LLM_CACHE" --cmake "$CMAKE" --output "$NEW_OUTPUT" --udid "$BOOTED_SIMULATOR_UDID"
python3 -m unittest discover -s packages/asr-runtime -p 'test_*.py' -v
python3 packages/asr-runtime/framework_report.py --output "$NEW_REVIEW_DIRECTORY"
```

Both output directories must be new. Only the aggregate report/export is suitable for CI publication; compiled frameworks, models and logs stay local. Framework signing class is inspected: unsigned device and toolchain ad-hoc simulator are evaluator artifacts, not developer distribution signing.


### Opt-in app framework build

`app_framework.py` builds the normal Eilo iOS simulator Release target using a
temporary copy of the Xcode project. Xcode links and embeds the reviewed simulator
framework through its normal Frameworks and Copy Files phases. Copy-phase stripping
is disabled in this temporary project so the embedded binary must match the
reviewed bytes exactly. The shipping project is not modified.

The script requires existing local `node_modules`, a **regular private copy** of
Pods at `apps/mobile/ios/Pods`, matching Podfile/Manifest locks, cached Release
archives for React Core, React Native Dependencies and Hermes, and generated
`build/rncore-facades`/`build/rndeps-facades`. A symlinked Pods directory is rejected
because Xcode resolves its project-relative paths from the real location. Reuse
approved local caches; do not run an installer or download missing dependencies.

Supply `--framework /reviewed/CEiloAsr.xcframework --output /fresh/output --udid
/already-booted-simulator-uuid`. The runner builds without developer signing,
checks the required framework load, verifies there are no named model/audio
resources, executes a separate Release guard probe, installs only on the named
simulator and checks three fresh ten-second process launches. It does not tap
Start, load a model, request microphone permission or establish UI/audio quality.
The probe grants only synthetic permission and confirms that default missing-model
readiness blocks capture and the Release ASR adapter remains unavailable.

Use `python3 app_framework_report.py` and `python3 -m unittest discover -p
'test_app_framework.py' -v` to audit
aggregate evidence without native caches. CI runs normal/optimized validation and
uploads only JSON/HTML summaries for seven days. All build products/logs and
absolute input paths remain local. Ordinary voice, physical, signing, distribution
and release acceptance remain open; persistent memory is disabled.
