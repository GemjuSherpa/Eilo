# S06 / VC-LLM-01 — Android CPU binding review

Gemju Sherpa reviewed and merged PR #43. Verified base is `568c34b3dac80afaec4cee9d0e8123eb0a8bb1a0`; all three PR #43 jobs passed. Requirement IDs: F06, F13, S01. VC-PACK-02 and VC-PACK-09 are approved dependencies. This checkpoint adds Kotlin/JNI evaluation to the reviewed native CPU core; VC-LLM-01 remains partial.

## Behavior and boundaries

Previously Android compatibility was a C++ syntax check. The Kotlin wrapper now owns one worker's native stream, borrows verified model descriptors/preformatted prompt bytes, and exposes bounded synchronous raw-piece callbacks. Supplied lease checks before/after load, prefill and decode reject revoked output. Fixed failures expose no backend cause/content. Scratch is reused and cleared after callbacks, including consumer failure; caller cleanup must use `use`/`finally`. Concurrent cancellation permanently marks the stream without waiting for decode. Worker cleanup detaches/destroys only after its active call returns; join the worker before releasing the stream.

JNI uses a bounded opaque ID registry with shared native lifetimes and per-entry worker gates. IDs are not pointers or reused values. Four live entries are allowed, including removed entries still active on a worker. Invalid/stale IDs and malformed arrays fail closed. Destroy removes the ID and signals cancellation; an active load/decode retains the core until return. No registry lock is held through model load or generation. Native scratch is cleared before release.

The fixed-name loader requires explicit Debug evaluation and grants no signed-pack readiness. Ordinary app source compiles, but runtime/model/evaluator packaging and production callers remain absent. The evaluator alone receives an ignored Gradle source/library/manifest overlay, removes INTERNET permission and verifies native socket denial. It hashes the exact private, immutable model descriptor later passed to the C++ core. The existing Q4 bytes and pinned official source remain unchanged. The normal APK is rebuilt/restored after evaluation, preserving app data and excluding evaluation files/classes/instrumentation.

## Validation — 13 October 2026

| Check | Result and scope |
| --- | --- |
| New JNI C++ | PASS with `-Wall -Wextra -Werror` for all four Android ABIs. |
| Kotlin focused regression | PASS: 21 tests covering unavailable defaults/loader gates, bounds, failure causes, borrowed split UTF-8, scratch reuse/clear, lease revocation, exactly-once cleanup and concurrent cancellation. |
| Full Android regression | PASS: 164 tests, zero failures/errors/skips; `lintDebug`, normal `assembleDebug` and `compileReleaseKotlin` pass using offline dependencies. |
| Real CPU completions | PASS: three frozen generic prompts, eight tokens each, on API35 ARM64 emulator in Kotlin/ART/JNI. CPU-only backend registry verified. |
| Real lifecycle cases | PASS: pre-cancel, corrupt GGUF, post-token cancel, post-decode lease revocation, concurrent load cancellation, concurrent begin cancellation and destroy during load. The destroy/load fixture observes the held native worker gate before removing the ID; actual native load returned CANCELLED (-2). Other timing races allow cancellation before/after a fast call; subsequent output is rejected. No physical latency claim. |
| JNI boundary cases | PASS: four-entry cap, malformed arrays, stale/nonreused IDs and invalid IDs. |
| Evaluation network boundary | PASS: INTERNET permission absent and actual IPv4 TCP, IPv6 TCP and IPv4 UDP socket creation denied. No connections, DNS or sends are attempted. Normal app/network privacy remains a separate gate. |
| Cross-ABI links | PASS: arm64-v8a, armeabi-v7a, x86, x86_64 at API26; only ARM64 executes. System-only dynamic dependencies and minimum 16 KB ELF LOAD alignment checked. Emulator uses 4,096-byte pages; no 16 KB page execution/ZIP claim. |
| Source/model provenance | Original llama.cpp v0.6.0 source archive/tree verified; unchanged S03 Q4 SHA-256 and 1,282,439,424 bytes verified on host and exact device descriptor. |
| Normal APK restoration | PASS: generic temporary model removed; normal APK has no evaluation library/assets/DEX classes/instrumentation. App data preserved. |
| Same iPhone simulator | Normal Debug app build/install PASS; three fresh ten-second launches PASS on iPhone 18 Pro/iOS27.0. This app startup check performs no LLM inference. |
| Secret scans | PASS: zero findings in all 11 intended source/review/result files and existing Git history, with redacted reports. No staged scan is claimed. |
| Workspace | ESLint/TypeScript PASS; nine mobile and 33 contract tests PASS. |

Exact generic outputs, build settings and binary hashes are in [Android results](../../packages/llm-runtime/tests/android-results.json). The first native evaluation and restoration passed; after cleanup and active-worker race hardening, the final evaluator was rerun. Ordinary JNI objects also compile for all four ABIs with the test worker probe absent without the evaluation define. A temporary automatic permission-review timeout required one retry; the retry was allowed. This was not an inference failure or a security verdict.

The evaluator's probe source intentionally references `socket`; inference archives have no listed network clients. Known ggml fatal-backtrace fork/execlp references remain and are recorded. Existing process-wide content-free log/fatal/terminate hooks remain; assertions still terminate. Android fork denial is not claimed. Vendor allocator/logits erasure is unverified, even though owned scratch/KV cleanup exists.

## Review and next task

See [reproduction commands](../../packages/llm-runtime/README.md#android-kotlinjni-binding-evaluation). No tools/services were purchased, installed or provisioned; existing Xcode, Gradle, NDK, source and model were reused. Evaluation APK installation was limited to the existing local emulator. No physical inference, microphone, signed production pack/controller attachment, chat quality/non-thinking configuration, speech policy or whole-app privacy acceptance is claimed.

Review the Kotlin/JNI lifetime/error boundary and isolated evaluator. Next dependency-ready work within VC-LLM-01 is current signed-pack/controller attachment on native workers. VC-LLM-02 must configure actual non-thinking behavior before conversational release. Physical quality/RAM/thermal/latency and retention gates remain open.

Source control follows the standing Gemju Sherpa authorization and continued task scope: `task/s06-vc-llm-01-android-binding` → `sprint/s06-android-llm-binding` → PR to main for review. The supplied documentation-only/no-Git entry excerpt is superseded by the recorded direct authorization for the remainder of the project. Personal signing/plist ordering/S02 review deltas are preserved exactly and excluded from this task. Local test success does not authorize a main merge. Stop for Gemju Sherpa review.
