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
