# S06 / VC-LLM-01 — Android controller worker review

PR #45 is reviewed and merged at `a6ec05326010dc6286c11c804b8e04938bbd89e7`; all three hosted jobs passed. Gemju Sherpa authorizes the next checkpoint with the same task → sprint → PR workflow. Requirements: F06, F13, S01. Dependencies VC-PACK-02 and VC-PACK-09 are approved; parent VC-LLM-01 remains partial.

## Result

The signed model lease previously required its caller to coordinate a worker and signal cancellation. Android now has `LlmControllerJob`: the controller registers one ticket for its current thinking turn before scheduling; the separate native worker resolves the signed pack, hashes/opens the descriptor, loads the CPU stream, prefills and consumes bounded borrowed raw pieces. No inference, file hashing, worker join or destruction runs under the controller monitor. The default thread guard rejects the Android main thread, and an inline executor is rejected before model IO. The default API remains unavailable; the ordinary app has no caller, packaged LLM or model-readiness override.

Stop, privacy transitions, permission changes, route disconnection, Pause, End, generation cancellation and interruption invalidate the ticket and signal the current native handle. The stream's cancellation signal is registered before the potentially long load. Stop does not wait for native decoding/destruction; the worker closes its stream/lease and exposes an explicit completion barrier after cleanup and controller detachment. Awaiting under the controller monitor is refused. Shutdown must await this barrier and terminate the dedicated executor off UI/controller/capture threads.

Submission transfers exclusive ownership of the bounded prompt byte array even when rejected; callers must cease access. Queued cancellation clears it immediately. During active synchronous prefill it remains exclusively borrowed until cancellation returns, then clears without a concurrent writer. Borrowed token scratch clears after each callback. The native worker also enforces the requested output-piece budget, independently of the CPU core. Each raw callback and final completion revalidate the controller token and disk-free pack epoch under the controller monitor. Old completion cannot affect a restarted turn. Missing runtime, changed pack, IO/native failure, broken scheduling/thread eligibility and cleanup errors expose fixed native outcomes and safe controller error codes; backend messages never enter diagnostics or snapshots.

Raw consumers may perform only bounded native buffer work and must not retain the scratch. They grant no speech/display/storage permission. A completed job stays thinking until separately approved non-thinking and speech-policy integration. Controller callbacks cannot join a worker or do IO/inference. Arbitrary in-place model mutation is still outside the immutable private-slot contract; pack revocation rejects output but does not itself interrupt an already active call. Executor lifecycle, native prompt formatting and speech-safe buffering remain the future caller's responsibilities.

## Actual verification

| Check | Result |
|---|---|
| Focused Kotlin tests | PASS: 22 tests for signed worker execution, thread eligibility, prompt/piece ownership, bounds, missing runtime, stale/foreign/duplicate tickets, queued and active load/prefill/decode cancellation, every privacy transition, permission/route/Pause/End/interruption, pack revocation during decode/end-of-stream, failed signals, close failures, stale completion and cleanup barrier. |
| Full Android suite and normal build | PASS: 202 tests, no failure/error/skip; Debug Kotlin compile, lintDebug, normal assembleDebug and Release Kotlin compile. Existing Gradle warnings remain. |
| Actual Android CPU | API35 ARM64 emulator executes the same three generic eight-token completions through signed pack → descriptor → controller worker → JNI CPU. The evaluator observes the actual JNI worker gate during model load before controller Stop; no stopped piece is released, destruction occurs once, and the prompt clears. Completion stays thinking without speech; callback runs off main under the controller monitor and borrowed prompt/piece buffers clear. |
| Existing native cases | Seven lifecycle, four registry/bounds, three default-gate and three signed pack/descriptor cases remain checked. Four strict ABI links/ELF/dependency checks pass; only ARM64 executes, with 4 KB pages. This is not physical/16 KB device execution. |
| Network/restoration | Evaluation APK has no INTERNET permission; IPv4 TCP, IPv6 TCP and IPv4 UDP socket probes are denied without connection/send. Temporary signed model/store removed and normal APK restored without evaluator libraries/assets/classes/instrumentation, preserving app data. Normal app network capability is unchanged. |
| Swift regression | PASS: 146 existing Swift tests. This checkpoint adds no Swift worker or iOS model execution. |
| Normal iOS app | PASS: same iPhone 18 Pro/iOS27 simulator Debug build/install and three fresh ten-second launches before commit. Home screenshot inspected: normal guest/stopped screen and model-setup gate. App startup is not inference. |
| Workspace | ESLint/typecheck, nine mobile and 33 contract tests PASS. |

The first platform-main-thread guard attempt could strand a job when the unmocked Android API threw in JVM tests. Its failure is now mapped to a completed unavailable outcome; the explicit synthetic worker eligibility seam is confined to native tests, and default Android behavior is exercised in the emulator. Review also added final completion-time pack verification, with an end-of-stream regression; the final native evaluator was rerun successfully after that change. The initial iOS launch checks used the Android identifier and then compared an installed process to its build-source path. Correct verification reads the actual identifier from the built iOS plist and checks the installed app container; all three fresh launches pass.

The emulator signs only a synthetic manifest with an ephemeral test key and synthetic license-evidence approval, using the unchanged reviewed Q4 model. This is no production trust/license approval or physical microphone trial. Runtime/model source and binary caches remain ignored. Vendor allocator/logits erasure, fatal-process behavior, physical latency/RAM/thermal/endurance and whole-app privacy remain open.

## Reproduce and review

Use existing tools and caches; no installation or download is required for this checkpoint. From `Eilo/apps/mobile/android`, with installed `JAVA_HOME` and `ANDROID_HOME`:

```sh
./gradlew :app:compileDebugKotlin :app:lintDebug :app:testDebugUnitTest --tests 'com.eilo.foundation.LlmControllerJobTest' --offline --max-workers=2
./gradlew :app:testDebugUnitTest :app:assembleDebug :app:compileReleaseKotlin --offline --max-workers=2
```

The [runtime instructions](../../packages/llm-runtime/README.md#android-controller-worker) describe explicit emulator evaluation; [recorded generic results](../../packages/llm-runtime/tests/android-results.json) include exact controller cases and build metadata. Synthetic readiness/permission effects are evaluator-only and open no microphone.

Review the ticket identity/monitor boundary, cancellation publication before load, transferred prompt lifetime, borrowed callback contract, final epoch verification and cleanup barrier. Next is the Swift controller-worker equivalent. Production app attachment, configured release trust/licensing, non-thinking configuration, speech policy and physical inference remain open. No complete S06/voice acceptance is claimed.

Source control: `task/s06-vc-llm-01-android-worker` → `sprint/s06-llm-controller-worker` → PR to main for Gemju Sherpa review. Personal Xcode signing/formatting, plist ordering and S02 review edits are preserved and excluded. No main merge or deployment; stop for review.
