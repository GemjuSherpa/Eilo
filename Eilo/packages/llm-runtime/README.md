# Native CPU model adapter — VC-LLM-01

This C ABI loads the reviewed Qwen3-1.7B Q4_K_M artifact into **in-process C++** and generates bounded raw token pieces with greedy sampling. One native worker owns a handle; another thread may permanently cancel it. CPU model loading and decode callbacks observe cancellation. Failure/cancellation frees the context, sampler, batch and model, clears KV storage, and returns no piece from the interrupted step. Owned temporary prompt tokens and piece scratch are cleared before release.

The model is loaded from a duplicated, independently verified open file descriptor. The caller must maintain an immutable file and exclusive descriptor-offset use; the adapter checks regular-file size, Qwen3 architecture and Q4_K_M metadata. It does **not** calculate or accept a signed manifest proof. Production callers must supply a current verified pack lease and recheck controller/session/privacy/model validity before releasing returned bytes. Cancellation arriving after a piece was returned is handled by that downstream generation check.

Bounds: 1–8 CPU threads, 4,096 total prompt/output tokens, 16,384 prompt bytes, 1–256 generated tokens, 128-token prefill batches, and 1,024 bytes per returned token piece. These are hard adapter safety limits; prompt trimming, memory budgets and continuation policy belong to later tasks. A raw piece can split UTF-8 and contains no speech authorization. No prompt/template, memory, tool, display or TTS integration is provided here. VC-LLM-02 must configure the actual non-thinking template before conversational release.

The normal mobile app compiles the Swift binding with an unavailable default and does not link/load this runtime or change its missing-model gate. The separate Swift simulator evaluation links and executes the actual CPU runtime; device SDK linking is also checked. Kotlin binding, trusted production attachment, physical inference/quality/performance and vendor allocator/logits retention remain open. The KV clear is not a complete private-memory erasure claim. The adapter suppresses llama/ggml process-wide logs and installs content-free fatal/terminate hooks; fatal assertions still terminate the process. A future shared-runtime integration must retain this logging boundary and review these process-wide hooks.

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

This checkpoint leaves VC-LLM-01 partial. Production signed-pack/controller attachment, Kotlin binding, non-thinking configuration, downstream speech policy and physical performance/retention evidence remain separate work.
