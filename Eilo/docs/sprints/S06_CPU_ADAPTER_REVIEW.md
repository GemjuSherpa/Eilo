# S06 / VC-LLM-01 — native CPU adapter review

Gemju Sherpa reviewed and merged PR #41, then authorized the next dependency-ready task with the same Git workflow. Verified base: `f775ee94217e39cac8625e204249f13321ab82d7`. VC-PACK-02's Q4 artifact and VC-PACK-09's readiness policy are approved. This checkpoint adds the shared in-process C++ adapter and real CPU host evidence. The parent task remains partially verified until native mobile bindings, verified pack/controller attachment and phone execution are tested.

## Behavior

Before this task, Eilo had verified Q4 model bytes and a native readiness policy but no local reply-generation adapter. `packages/llm-runtime` now exposes a C ABI that loads the exact reviewed artifact from an independently verified open descriptor and generates bounded raw token pieces with CPU-only parameters. The same descriptor is hashed before inheritance by the real test; no model pathname is reopened by the adapter.

One worker owns each handle. Cancellation is permanent and can be signalled by another thread during loading or decoding. Vendor load-progress/CPU-abort callbacks and post-call checks reject the interrupted step. Failure/cancellation clears and frees the context, batch, sampler and model; repeated completion cannot release a second token. Owned prompt-token and piece scratch is cleared. The downstream native controller must still reject bytes returned before a later Stop/privacy/model change.

Limits are 4,096 total prompt/output tokens, 16,384 prompt bytes, 1–256 generated tokens, 128-token prefill batches, 1,024 bytes per raw piece and 1–8 CPU threads. Token pieces can split UTF-8. This task does not configure a conversational/non-thinking template or approve output for speech. Actual chat-template configuration is VC-LLM-02; prompt/memory budget policy is VC-LLM-03.

The runtime is official llama.cpp v0.6.0 at `8345f333951c661d166b00e6f9362e553768f292`, with the archive hash recorded in [provenance](../../packages/llm-runtime/provenance.json). The previously installed conversion checkout's reported revision could not be verified against the official public source, so a separately pinned source archive is used for inference. S03's Q4 bytes/hash remain unchanged. Runtime preparation, CMake and Python are build/test tooling only; inference itself executes in C++ without a local server or Python inference.

## Validation — 12 October 2026

| Check | Actual result and boundary |
| --- | --- |
| C++ compiler warnings | PASS with `-Wall -Wextra -Werror`. |
| Scripted C API lifecycle/bounds/failure/cancellation | PASS: 27 scenarios with ASan/UBSan. Vendor release libraries are not sanitizer-instrumented. |
| Source/download integrity fixtures | PASS: eight Python tests in ordinary and optimized modes. Edits/extras/symlinks/traversal/duplicate entries, changed download and foreign redirect are rejected without replacing the previous archive. |
| Real native Q4 CPU execution | PASS: three frozen generic completions, each capped at eight tokens. The registry exposes CPU devices only; GPU/Metal/BLAS/RPC/dynamic backends and common/server/network tools are disabled. |
| Real lifecycle fixtures | PASS: invalid descriptor, corrupt GGUF, pre-cancel, post-token cancellation, concurrent begin cancellation and concurrent load cancellation. |
| Offline process boundary | PASS: the inference process denies all networking and child creation. IPv4 TCP, IPv6 TCP, UDP and fork probes return permission denial before model tests. This is not a phone offline-conversation test. |
| Static library audit | Network references absent. Known `fork`/`execlp` references remain in ggml's fatal backtrace code and are recorded. Eilo installs content-free fatal/terminate hooks; assertions still terminate. Evaluation denies fork. |
| Mobile C++ source compatibility | PASS: Android ARM64/ARMv7/x86/x86_64 at API 26; iOS ARM64 device/simulator at deployment target 18. Syntax compilation only, no mobile runtime link/execution claim. |
| Same iPhone 18 Pro / iOS 27.0 simulator | Debug app build PASS; install and three fresh ten-second launches PASS before commit. The normal app does not link this new evaluation adapter. |
| Workspace JS checks | ESLint/TypeScript PASS; nine mobile and 33 contract tests PASS. |
| Hosted regression coverage | Existing workflow now runs the eight source/download integrity fixtures in both Python modes without runtime or model downloads. Real CPU host checks remain local. |

Frozen generic outputs and exact build configuration are in [host results](../../packages/llm-runtime/tests/host-results.json). These raw completions demonstrate native execution, not conversation quality, emotional understanding, non-thinking behavior or safety. No real user prompt, microphone audio or personal history was used. No quality/performance gate is promoted from these results.

## Reproduction and remaining work

See [CPU adapter README](../../packages/llm-runtime/README.md) for exact preparation and verification commands. `python3 Eilo/packages/llm-runtime/check_host.py` verifies the source inventory/model descriptor, builds the CPU libraries, runs sanitizer contract tests and executes the real network-denied evaluation. Model/vendor/build artifacts stay ignored. Existing MIT/Apache license texts match the selected source/model directions; the complete mobile distribution inventory remains a release gate.

The normal app retains its missing-model gate. Swift/Kotlin bindings, current signed-pack/controller leases, actual non-thinking configuration, speech policy, physical phone inference/RAM/thermal/battery/background behavior and vendor allocator/logits erasure remain open. Clearing owned scratch and KV storage is not a complete private-memory or compliance pass. Logging/fatal hooks are process-wide and must be reviewed when integrating multiple native runtimes. Fatal vendor assertions cannot be converted into recoverable C ABI errors.

Source control follows `task/s06-vc-llm-01-cpu-adapter` → `sprint/s06-local-reply` → PR to main for Gemju Sherpa review. Personal Xcode signing/formatting, plist ordering and unrelated S02 review edits remain local and excluded. No paid service, deployment or main merge is performed. The next checkpoint is native mobile binding and verified controller/pack attachment for VC-LLM-01; this PR does not mark S06 complete.
