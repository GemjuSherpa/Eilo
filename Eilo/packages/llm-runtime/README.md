# Native CPU model adapter — VC-LLM-01

This C ABI loads the reviewed Qwen3-1.7B Q4_K_M artifact into **in-process C++** and generates bounded raw token pieces with greedy sampling. One native worker owns a handle; another thread may permanently cancel it. CPU model loading and decode callbacks observe cancellation. Failure/cancellation frees the context, sampler, batch and model, clears KV storage, and returns no piece from the interrupted step. Owned temporary prompt tokens and piece scratch are cleared before release.

The model is loaded from a duplicated, independently verified open file descriptor. The caller must maintain an immutable file and exclusive descriptor-offset use; the adapter checks regular-file size, Qwen3 architecture and Q4_K_M metadata. It does **not** calculate or accept a signed manifest proof. Production callers must supply a current verified pack lease and recheck controller/session/privacy/model validity before releasing returned bytes. Cancellation arriving after a piece was returned is handled by that downstream generation check.

Bounds: 1–8 CPU threads, 4,096 total prompt/output tokens, 16,384 prompt bytes, 1–256 generated tokens, 128-token prefill batches, and 1,024 bytes per returned token piece. These are hard adapter safety limits; prompt trimming, memory budgets and continuation policy belong to later tasks. A raw piece can split UTF-8 and contains no speech authorization. No prompt/template, memory, tool, display or TTS integration is provided here. VC-LLM-02 must configure the actual non-thinking template before conversational release.

The normal mobile app compiles Swift and Kotlin bindings with unavailable defaults and does not link/load this runtime or change its missing-model gate. Separate Swift simulator and Kotlin/JNI emulator evaluations execute the actual CPU runtime; iOS device SDK linking and all four Android ABI links are checked. Trusted production attachment, physical inference/quality/performance and vendor allocator/logits retention remain open. The KV clear is not a complete private-memory erasure claim. The adapter suppresses llama/ggml process-wide logs and installs content-free fatal/terminate hooks; fatal assertions still terminate the process. A future shared-runtime integration must retain this logging boundary and review these process-wide hooks.

## Pin and licensing

[provenance.json](provenance.json) records the official [llama.cpp v0.6.0 release](https://github.com/ggml-org/llama.cpp/releases/tag/v0.6.0), exact commit and source archive checksum. The installed older conversion checkout was not used as the new inference runtime because its reported revision could not be verified against the official source. Runtime preparation does not change the approved S03 model bytes or repeat quantization.

llama.cpp is MIT; the Qwen model is Apache-2.0. Existing texts are in [model licenses](../../docs/models/licenses). A complete mobile runtime/model distribution inventory remains a release gate. Source, static libraries, model weights, executables and build logs remain in ignored `.local` caches; no personal prompt or audio is used in evaluation.

## Reproduce

The host evaluation uses macOS ARM64, Xcode's `clang++`, Python 3.12+ and the existing build-only CMake environment at `.local/model-build/venv/bin/cmake`. It does not install dependencies. Other host toolchains and physical phone execution are not established by this script.

From `Eilo`, explicitly prepare the generic source once:

```sh
python3 packages/llm-runtime/prepare_source.py
```

For ordinary source/lifecycle checks (no model required):

```sh
python3 -m unittest discover -s packages/llm-runtime -p 'test_*.py'
python3 -O -m unittest discover -s packages/llm-runtime -p 'test_*.py'
python3 packages/llm-runtime/check_host.py --contract-only
```

For real CPU execution, first provide the unchanged [S03 Q4 artifact](../../docs/models/evidence/q4-k-m.json) at `.local/model-build/qwen3-1.7b-q4-k-m.gguf`, then run:

```sh
python3 packages/llm-runtime/check_host.py
```

The script verifies the pinned archive and every extracted source file, rejects extras/symlinks/edits, builds only static CPU inference libraries, inspects their undefined symbols and hashes the same model descriptor inherited by the test executable. Network references are absent. Official ggml fatal-backtrace code retains `fork`/`execlp` references; the report records them rather than claiming absence. Inference runs under `sandbox-exec` with all network operations and child-process creation denied. IPv4 TCP, IPv6 TCP, UDP and fork probes must return permission denial before model tests begin. Eilo's fatal hooks avoid vendor backtrace/debugger attachment; this does not certify the future mobile process sandbox. Build/source preparation may use networking separately; inference does not.

Actual evaluation includes three generic raw completions, invalid descriptor/corrupt GGUF failure, pre-cancel, post-token cancellation, concurrent begin cancellation and concurrent load cancellation. Scripted C API fixtures separately cover 27 lifecycle/bounds/error scenarios with ASan/UBSan. Sanitizers do not instrument the release vendor libraries. Concurrent host cancellation is not a physical latency/p95 measurement, and raw completions are not a chat-quality or non-thinking pass.

The final report is `.local/llm/host-results.json`; [published frozen results](tests/host-results.json) include generic synthetic outputs only. Normal app regression uses the existing same iPhone 18 Pro simulator build/three-launch check. That app run does not execute this separately evaluated CPU adapter.

## iOS Swift binding evaluation

`NativeLlmStream` uses one serialized native worker for loading, generation and cleanup. `requestCancellation` can run concurrently: a short handle-lifetime lock protects the atomic C cancellation call without waiting for decode or destroying its active handle. The worker clears its 1,024-byte scratch after each borrowed callback and rechecks the supplied current controller/privacy/model lease before releasing a raw piece. A piece may split UTF-8 and remains unapproved for speech. The consumer must also recheck its controller transaction before later display/playback/storage. Join the worker before releasing its last reference; a Swift object cannot fix misuse of this ownership contract.

The descriptor must already be hashed, immutable and exclusively borrowed until load returns. The wrapper accepts no model pathname, creates no file/network client and retains no prompt String. The evaluator opens a native pathname separately and hashes the same descriptor that C++ subsequently duplicates. Its permissive synthetic lease is an evaluation fixture, not production manifest verification.

The real API requires all three conditions: the `CEiloLlm` header module, `DEBUG`, and `EILO_LLM_EVALUATION`. Merely making headers available, defining Debug alone or defining the evaluation flag alone preserves the unavailable default. Normal app builds add only Swift source compilation; no runtime libraries/model/assets/readiness override are added.

From `Eilo`, with the existing pinned source and Q4 artifact, select an existing booted simulator explicitly:

```sh
python3 packages/llm-runtime/check_ios.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8
```

For simulator/device SDK link checks without model execution:

```sh
python3 packages/llm-runtime/check_ios.py --compile-only
```

The script verifies all original source files, downloads nothing, builds ARM64 iOS CPU static libraries with Metal/GPU/RPC/dynamic backends/server/network tools disabled, and links Swift/C++ for both SDKs. It runs three frozen generic completions, six real lifecycle fixtures and three default-gate configurations on the chosen simulator. The library registry must contain CPU devices only. Results go to `.local/llm/ios-results.json`; [published results](tests/ios-results.json) retain only generic fixtures, build hashes and scope boundaries. Runtime/source/binary/model files stay ignored. No microphone or physical iPhone execution occurs. Listed network symbols are absent, but OS-wide networking isolation for the simulator process is **not verified**; the earlier host sandbox result does not establish phone isolation.

Focused lifetime/lease/error tests run as part of the existing Swift package and CI:

```sh
cd packages/native-test-seam
swift test --filter NativeLlmStreamTests
```

This checkpoint leaves VC-LLM-01 partial. Production signed-pack/controller attachment, non-thinking configuration, downstream speech policy and physical performance/retention evidence remain separate work.

## Android Kotlin/JNI binding evaluation

`NativeLlmStream.kt` borrows an already verified immutable descriptor and bounded preformatted prompt bytes on one serialized worker. It checks the supplied current lease before and after native calls, exposes raw pieces through a synchronous borrowed 1,024-byte scratch, and clears scratch after every callback. Only `requestCancellation` runs concurrently; close/destruction belongs to the worker after decode returns. Join the worker before releasing its last stream reference. Prompt, descriptor and raw output do not cross JS. Consumers must revalidate downstream controller transactions before display, speech or storage.

JNI IDs are opaque, positive and never reused during the process. A four-entry lifetime bound includes removed entries still retained by an active worker. Per-entry worker gates reject concurrent decode/load calls; a brief registry gate protects lookup/removal. Cancellation does not wait behind model decoding. Destroy invalidates the ID and atomically cancels; an active call retains the C core until returning. Invalid IDs/array lengths are rejected without dereferencing arbitrary pointers. Scratch copies in C++ are cleared on exit.

`NativeLlmRuntime` attempts the fixed app-packaged `eilo_llm_jni` library only when explicitly enabled in Debug. Its ABI probe grants no model trust/readiness. The ordinary app never calls this loader and packages no runtime/model/evaluator. A failed loader instance never retries. Unit tests cover defaults, fixed loading, failure mapping, bounds, split UTF-8, lifetime, revocation and concurrent cancellation.

From `Eilo`, with the existing pinned source/model and booted API35 ARM64 emulator:

```sh
python3 packages/llm-runtime/check_android.py \
  --ndk /Users/gemju/Library/Android/sdk/ndk/27.1.12297006 \
  --java-home /opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
  --android-sdk /Users/gemju/Library/Android/sdk \
  --serial emulator-5554
```

Use your installed paths and the explicit existing emulator serial. `--compile-only` skips emulator execution and needs no serial. The script verifies the original source, builds CPU static libraries and strictly compiles/links the binding for arm64-v8a, armeabi-v7a, x86 and x86_64 at API26. GPU/RPC/dynamic backends/server/network tools are disabled. ELF LOAD segments have at least 16 KB alignment; this is not 16 KB page-size execution or ZIP packaging evidence. The other three ABIs are link-only, and 32-bit model execution/performance is not established.

An ignored Gradle init file adds only the explicit evaluator source and ARM64 library to a temporary Debug APK. The manifest removes INTERNET permission. The evaluator checks actual permission denial and native IPv4/IPv6 TCP/IPv4 UDP socket denial before inference; these probes initiate no connection or send. The generic model is streamed into a private temporary slot, hashed using the exact descriptor later borrowed by C++, and deleted afterwards. No microphone or personal data is used.

Three generic eight-token completions, seven real lifecycle cases, four JNI registry/bounds cases and three default-gate cases execute in Android ART. The release-flag gate is tested inside Debug, not by executing a Release APK. Failure/timeout cleanup stops the evaluator and attempts to restore a complete normal APK even if temporary-file cleanup fails. Restoration checks absence of the evaluation library/assets/DEX classes/instrumentation and preserves existing app data. A restoration failure fails the command rather than publishing a successful report. Results are in ignored `.local/llm/android-results.json`; [recorded results](tests/android-results.json) contain generic fixtures and build metadata only.

The evaluation APK has no Internet permission; the restored normal app retains its existing network capabilities. This isolated result does not establish whole-app traffic privacy or physical Android/iPhone inference. ggml's known fatal-backtrace fork/execlp references remain reported; Android process-fork denial is not claimed. Actual non-thinking configuration, speech policy, vendor retention and production signed-pack/controller attachment still gate conversational use.

## Verified pack model opening

Native Kotlin/Swift `LlmPackLease` resolves a signed-store snapshot against reviewed native configuration: exact pack/runtime, artifact ID, role `llm`, `.gguf`, SHA-256, byte count, Apache-2.0 and license-evidence hash. It selects by ID rather than manifest order. Signature, runtime compatibility, all file hashes and configured license approvals must pass first. There is no JS selector or default production trust/key/caller configuration.

Resolve and open on one native worker. `openStream` combines the revocable store epoch/lease with the caller's current controller/session/privacy predicate. It rejects invalid state before opening, after descriptor hashing, after model load and after descriptor close. Replacements and failed activation revoke outstanding leases even when model bytes are unchanged. The stream rechecks the combined predicate after decode and clears/rejects stale pieces. The controller must separately call `requestCancellation` to interrupt an active native call and join its worker before releasing it. Later display/speech/storage transactions also require their own current-generation checks.

The default native opener uses read-only/no-follow/nonblocking/close-on-exec flags, rejects nonregular files and wrong sizes, hashes the same open descriptor in 64 KB scratch, rewinds it and borrows it into the C++ loader. The C core duplicates the descriptor before the wrapper closes it. Hash, native load and close failures cannot publish a stream; raw backend errors do not escape. A path replacement after hashing cannot substitute another file for that open descriptor. The caller still keeps app-private slots immutable and revokes before known maintenance; arbitrary in-place modification after hashing is not prevented by this API.

Android's public atomic duplication/flag verification API is available from API30; this opener fails closed on older runtimes. The app foundation remains API26 and the proposed model cohort remains Android15+/8 GB. API30 physical execution is not established by this gate. Darwin uses the corresponding native flags. A copied read-only Android model now syncs through a read descriptor, preserving source/destination protection instead of requiring a writable reopen.

The same explicit Android evaluator now runs the three generic real Q4 completions through an ephemeral signed pack and this descriptor boundary. It injects an activation failure at the verified before-pointer boundary, then rejects a piece already decoded from the old epoch. Native tests also reject wrong hash/size, symlink, directory and FIFO descriptors and verify close. The fixture's generated signing key and synthetic license-evidence token are test-only; no production trust/license approval is installed. The temporary signed store/model is removed and the normal APK restored. [Review and exact coverage](../../docs/sprints/S06_LLM_PACK_LEASE_REVIEW.md) distinguishes actual Android CPU execution, Darwin descriptor tests and remaining physical/production gates.

Focused tests, using existing toolchains:

```sh
# From Eilo/apps/mobile/android with installed JAVA_HOME/ANDROID_HOME:
./gradlew :app:testDebugUnitTest --tests 'com.eilo.foundation.LlmPackLeaseTest' --offline --max-workers=2
# From Eilo/packages/native-test-seam:
swift test --filter LlmPackLeaseTests
```

The ordinary app still has unavailable runtime/model readiness. Configured release trust, physical inference/performance, non-thinking configuration, speech policy and vendor allocator/logits retention remain open.

## Android controller worker

`LlmControllerJob` registers a controller-issued ticket before scheduling one current thinking-turn job on a separate native executor. It resolves a signed `LlmPackLease`, publishes the stream's short cancellation signal before loading, and exclusively owns load/prefill/decode/close. Default Android main-thread and inline-executor execution are rejected before model IO. No ordinary app caller, runtime packaging or readiness override is installed.

Submission transfers exclusive ownership of the bounded prompt byte array, including on rejection. Cancelled queued prompts clear immediately; an active prefill keeps the prompt borrowed until the native call returns, then clears it. Stop/privacy/generation/route/permission transitions invalidate tickets and signal native cancellation without joining/destructing inside the controller. Raw borrowed pieces and final completion revalidate the token and pack epoch under that same controller monitor. Consumers must perform only bounded native buffer work, retain no scratch and do no IO, inference or joining there. Completed raw generation stays thinking and grants no speech/display/storage rights.

`awaitCompletion` is a lifecycle cleanup barrier after prompt/native/lease cleanup and controller detachment, not a latency claim. Await it and terminate the dedicated executor off UI/controller/capture threads before releasing worker resources. Pack revocation rejects output but does not independently interrupt an active call; private model slots remain immutable. Prompt formatting, non-thinking configuration, speech policy and vendor-retention evidence remain separate gates.

The same explicit `check_android.py` command above runs three real generic eight-token completions through this worker on the existing API35 ARM64 emulator, observes the actual JNI load gate before controller Stop, and verifies once-only destruction, prompt/piece clearing and no speech state. All previous native cases, denied socket probes and normal APK restoration remain required. Signing and license configuration and controller permission/readiness effects are synthetic evaluator-only; no microphone is opened. Swift worker integration and physical inference are not verified by this Android run.

Focused tests use the existing JDK/SDK from `Eilo/apps/mobile/android`:

```sh
./gradlew :app:testDebugUnitTest --tests 'com.eilo.foundation.LlmControllerJobTest' --offline --max-workers=2
```

[Review scope and reproduction](../../docs/sprints/S06_ANDROID_LLM_WORKER_REVIEW.md) and [generic actual results](tests/android-results.json) keep the parent VC-LLM-01 acceptance partial.
