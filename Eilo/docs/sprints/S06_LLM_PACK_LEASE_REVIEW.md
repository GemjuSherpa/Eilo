# S06 / VC-LLM-01 — signed model lease review

PR #44 is merged at `797d1c1f5c6a4e9d7ba32ab35f96650d955c1e96`; all three hosted jobs passed. Gemju Sherpa authorizes the next task with the same task → sprint → PR workflow. Requirement IDs: F06, F13, S01; dependencies VC-PACK-02 and VC-PACK-09 are approved. This is the model-trust boundary checkpoint of VC-LLM-01, whose parent acceptance remains partial.

## Result

The CPU bindings previously accepted descriptors whose verification was the caller's responsibility. Kotlin and Swift now provide `LlmPackLease`: signature/runtime/license/all-file verification through the existing store, exact native pin matching by ID, a revocable epoch, and same-open-descriptor SHA-256/size verification before native loading. The selected signed artifact must be the expected `.gguf` LLM, digest, size, Apache-2.0 model and license-evidence hash; manifest ordering never selects it.

One serialized worker resolves, hashes, loads and closes the borrowed descriptor. The combined pack/controller predicate is checked before/after those steps and before releasing decoded pieces. Store replacement, failed activation, explicit lease close and caller Stop/privacy invalidation reject stale work. Close failures cannot return a loaded stream. Raw failures expose fixed typed errors. The controller separately signals concurrent native cancellation and joins the worker; this lease alone does not interrupt an active call. Downstream transactions must revalidate before display, speech or storage.

Native descriptor opening is read-only, no-follow, nonblocking and close-on-exec, so symlinks/directories/FIFOs cannot become models. Atomic Android descriptor duplication preserves and verifies close-on-exec flags; Darwin flags are checked in native tests. Hashing uses bounded cleared scratch and rewinds the same descriptor borrowed into C++; pathname replacement cannot substitute different bytes. Slots still remain app-private/immutable with revocation before known maintenance; this is not an arbitrary post-hash in-place mutation detector. Android's public atomic duplication/flag check needs API30, so older opens fail closed while the foundation minimum remains API26. The proposed model cohort remains Android15+/8 GB; no API30 device performance claim is made.

Device evaluation found an existing activation defect: `Files.copy` preserves read-only model permissions, and opening the copied model for append solely to sync it fails. Activation now syncs via a read descriptor, preserving protection. The new read-only-source regression passes. A standalone reproduction rejects the old write-sync recipe and succeeds with the read-sync recipe without changing permissions.

## Validation — 13 October 2026

| Check | Actual result and scope |
| --- | --- |
| Kotlin compile and focused lease tests | PASS: 16 tests, including signed selection/mismatches, closed/replaced/failed epochs, opening/load/close races, error cleanup, actual controller Stop/privacy tokens and read-only activation. Native descriptor opening is tested separately on Android. |
| Swift compile and focused lease tests | PASS: strict source compilation; 18 tests. Actual Darwin descriptor tests hash/rewind/borrow/close, preserve the original inode through a pathname swap and reject hash/size/symlink/directory/FIFO failures. Backends in these tests are scripted; they are not iOS model inference. |
| Full native regression | PASS: 180 Android tests and 146 Swift tests, zero failures. Android lint, normal Debug build and Release Kotlin compilation pass. Lint caught the public SDK floors (API27 open flag/API30 duplication and flag check); a runtime API30 guard was added, without suppressing the error or raising the foundation minimum. Existing Android warnings remain. |
| Actual Android signed-pack inference | PASS on the existing API35 ARM64 emulator: three generic eight-token Q4 completions through generated ES256 test manifest → store activation → exact model lease → hashed descriptor → real JNI CPU runtime. Existing seven lifecycle/four registry/three default-gate cases still pass. |
| Actual native pack/descriptor cases | PASS: failed activation at before-pointer revokes an already decoded piece; descriptor validation rejects hash/size/symlink/directory/FIFO and verifies close. These are fixed synthetic fixtures, not physical timing trials. |
| Network and restoration | Evaluation APK has no INTERNET permission; IPv4 TCP, IPv6 TCP and IPv4 UDP socket probes are denied. Temporary model/signed store removed; normal APK restored without evaluator libraries/assets/classes/instrumentation, preserving app data. Whole-app networking/privacy remains separate. |
| Four Android CPU ABI links | PASS against unchanged pinned source; only ARM64 executes, with 4 KB pages. Existing 16 KB ELF alignment checks do not establish 16 KB device/ZIP execution. |
| Normal iOS app | New shared lease source added through four Xcode entries. Same iPhone 18 Pro/iOS27.0 simulator Debug build/install and three fresh ten-second launches PASS before commit. Startup performs no LLM inference. |
| Workspace | ESLint/TypeScript PASS; nine mobile and 33 contract tests PASS. |

Initial Android fixture attempts failed and restored the normal APK. Android's JSON writer escaped URL slashes, conflicting with the reviewed strict manifest grammar; the fixed generic payload is normalized before signing. Signed input/parser/signature rules are unchanged. The next attempt exposed the read-only sync defect above; the actual signed-model evaluation passed after its correction. Failure diagnostics contain fixed stage/type codes and no raw messages/paths/stacks. Source/runtime/model downloads, tool/service installation and paid services were not used.

Exact generic Android outputs/build metadata are in [results](../../packages/llm-runtime/tests/android-results.json). Reproduction is in [runtime instructions](../../packages/llm-runtime/README.md#verified-pack-model-opening). Existing source/runtime/model/license files remain ignored. The evaluator generates an ephemeral signing key and uses synthetic license-evidence approval; it installs no production trust or release approval. Vendor allocator/logits erasure, fatal-process behavior, whole-app traffic/privacy and physical phone quality/RAM/thermal/latency remain open.

## Review and next step

Review the signed pin/epoch boundary, descriptor lifetime and read-only activation fix. Swift signed-pack CPU inference on iOS and physical inference are NOT RUN for this checkpoint. Production release trust/configuration and the controller's worker/ticket/cancellation attachment remain absent; ordinary runtime/model readiness remains unavailable. Non-thinking configuration and speech policy are separate tasks. No complete S06 or voice acceptance is claimed.

Source control: `task/s06-vc-llm-01-pack-lease` → `sprint/s06-llm-pack-lease` → PR to main for Gemju Sherpa review. Only four new Xcode references belong to this task; personal signing/formatting, plist ordering and S02 review edits are preserved and excluded. No deployment or main merge. Stop for review.
