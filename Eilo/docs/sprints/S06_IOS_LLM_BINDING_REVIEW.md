# S06 / VC-LLM-01 — Swift CPU binding review

Gemju Sherpa reviewed and merged PR #42, then authorized the next task with the same scoped Git workflow. Verified base: `eb16070da8d25f5e914422f501411d6364be7941`; all three PR #42 jobs passed. Requirement IDs: F06, F13, S01. This is the iOS binding checkpoint of the existing CPU adapter task; parent acceptance remains partial.

## Behavior and scope

Previously only the C++ core executed real Q4 generation on macOS; native mobile source compatibility was syntax-only. `NativeLlmStream.swift` now owns the real C handle for one generation, borrows a previously verified model descriptor/prompt bytes, and exposes bounded synchronous raw-piece callbacks on one native worker. A separate cancellation path marks the handle permanently without waiting for decode. Handle detachment and the short atomic cancellation call share a lifetime lock, so cancellation cannot touch a destroyed pointer. Destruction and scratch clearing remain worker operations after its active native call completes. The caller must join that worker before releasing its last stream reference.

Current controller/privacy/model validity is checked before and after native loading, prompt prefill and each returned piece. Malformed native status/length, failure or revocation closes once and releases no callback. The scratch is cleared after every borrowed callback, including failure. A raw piece may split UTF-8 and cannot authorize speech. Any later display/playback/storage transaction must separately revalidate current controller/session/privacy/model state; a cancellation after a callback returns cannot be undone by this wrapper.

The normal Xcode app target compiles the Swift source with a fail-closed default. No C++ runtime/model is packaged or attached to the app. The real binding is available only with its native header module plus both Debug and explicit `EILO_LLM_EVALUATION`. Standalone generic evaluators link both iOS SDK variants against the unchanged, checksum-verified official llama.cpp v0.6.0 source; no vendor source patch is used. Swift opens/hashes the exact model descriptor later borrowed by C++, avoiding a pathname reopen after verification. The production signed-pack lease/caller is still absent.

## Validation — 12 October 2026

| Check | Actual result and boundary |
| --- | --- |
| Swift source build | PASS with warnings as errors. |
| Focused Swift lifecycle tests | PASS: 15 tests covering bounds, create/load/begin/error/close, raw split UTF-8, scratch reuse, revocation and concurrent cancellation of a blocked scripted decode. |
| Full Swift regression | PASS: 128 tests. A separate strict-all-tests attempt encountered pre-existing unused-result warnings in WakeDetectorTests; no warning suppression or unrelated test change was added. |
| Real iOS Swift/C++ CPU generation | PASS: three frozen generic completions, each capped at eight tokens, on the same iPhone 18 Pro/iOS 27.0 ARM64 simulator. CPU-only registry checked. |
| Real binding lifecycle fixtures | PASS: pre-cancel, corrupt GGUF, post-token cancel, post-decode lease revocation, concurrent load cancellation and concurrent begin cancellation. The concurrent cases reject subsequent pieces after cancellation joins; they are not physical cancellation-latency measurements. |
| Default gate matrix | PASS on simulator: ordinary headers, Debug alone and evaluation flag alone all remain unavailable without runtime linkage. |
| iOS simulator/device SDK runtime links | PASS: actual static runtime plus C++/Swift binding linked for ARM64 at iOS 18. Device execution/signing NOT RUN. |
| Library symbol audit | Listed network references absent. Known ggml fatal-backtrace fork/execlp references remain in both SDK libraries and are recorded. Existing process-wide content-free fatal hooks remain in effect; fatal assertions still terminate. Simulator OS-wide network isolation NOT VERIFIED. |
| Normal app regression | Debug app build/install PASS; three fresh ten-second launches PASS before commit on the same simulator. New Swift source is compiled, but the app does not perform LLM inference. |
| Workspace checks | ESLint/TypeScript PASS; nine mobile and 33 contract tests PASS. |

The actual generic outputs and exact options/library hashes are in [iOS results](../../packages/llm-runtime/tests/ios-results.json). Output wording differs from the earlier host raw completions; this is not a quality, non-thinking, deterministic cross-platform text, emotional understanding or speech-safety pass. The evaluator never opens a microphone and uses no personal conversation/history. Model/source/libraries/executables/logs stay in ignored local caches.

## Reproduction and remaining work

See [binding instructions](../../packages/llm-runtime/README.md#ios-swift-binding-evaluation). `python3 packages/llm-runtime/check_ios.py --udid <existing-booted-udid>` from `Eilo` verifies source, builds/links both SDKs and runs the standalone real model fixtures. `--compile-only` skips model execution. `swift test` in `packages/native-test-seam` runs the 128-test regression including the new binding tests. The existing local CMake/Python/Xcode tools and S03 model are reused; no paid service or dependency installation is required.

Next is the native Kotlin binding or verified production pack/controller attachment within VC-LLM-01. Those, physical iPhone inference/quality/RAM/thermal/background behavior, actual non-thinking template configuration, speech policy and vendor allocator/logits erasure remain open. Owned scratch/KV cleanup does not establish complete private-memory erasure. Linking a runtime does not establish model trust/readiness or physical acceptance. Default missing-model readiness remains unchanged.

Source control: `task/s06-vc-llm-01-ios-binding` → `sprint/s06-ios-llm-binding` → PR to main for Gemju Sherpa review. The four new Xcode source entries are isolated from existing personal signing/formatting edits; those, plist ordering and unrelated S02 review edits are preserved and excluded. No deployment or main merge is performed. Stop at this review checkpoint.
