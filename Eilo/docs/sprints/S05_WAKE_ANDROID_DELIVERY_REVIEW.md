# S05 Android wake-frame queue review

VC-TURN-02 / F03 / A02. Gemju Sherpa reviewed and merged PR #32; fetched base main `7022957`. Branches: `task/s05-vc-turn-02-android-delivery` → `sprint/s05-wake-android-delivery` → main PR awaiting review.

Android previously had the real Kotlin/JNI keyword binding but no bounded delivery queue. `WakeFrameDelivery` now copies native PCM16 prefixes into four fixed slots without decoding on submission. The native worker drains at most four frames per call, erases application slots/scratch, and returns activation metadata after releasing its locks. Stable rate, 100 ms frame bounds, less than 250 ms receive age and monotonic receive time are required. Overflow, stale/invalid input, route-rate changes and detector failure close the delivery and revoke prior metadata. Controller application checks both delivery and detector leases with the original generation. Close revokes first, then waits for any synchronous decode and erases buffers before returning.

This is a queue checkpoint. `ForegroundCapture` is unchanged and does not yet attach/feed/drain this queue. The existing capture worker continuously reads, so attachment must be reconciled within its lifecycle rather than simply enqueueing behind that read loop. Native capture attachment, detach on generation/lifecycle changes and metadata dispatch are the next task. No automatic JNI loading, production readiness, microphone permission, JS PCM, storage or ASR is added.

| Check before commit | Actual result |
|---|---|
| Normal Android Kotlin compiler / JUnit / lint | PASS: 101 tests, zero failures/errors/skips; eight new queue tests |
| Android Debug and Release packaging | BUILD SUCCESSFUL; normal app without evaluation libraries/models |
| Offline JNI compiler | PASS: all four Android ABI links, matching pinned host JNI library |
| Actual Kotlin queue/JNI/controller synthetic evaluation | PASS: all 28 entries; queued detections match direct decoding; 11 wake, zero activations across 15 nonwake, two excluded diagnostics, 24 unique WAVs; queued Stop rejection passes |
| Python integrity/report checks, normal and `-O` | PASS: five tests each; queued evidence is mandatory and strictly validated |
| Same iPhone 18 Pro / iOS 27.0 simulator | Debug BUILD SUCCEEDED; installed app passed three fresh ten-second launches |
| Android device/emulator or microphone execution | NOT RUN |
| Staged diff and secret scan | PASS before commit |
| Hosted checks | Pending at PR publication |

The queue tests exercise prefix copy, worker-only decoding, erased buffers, overflow revoking an already returned event, invalid bounds/rate, stale boundary/backwards clock, four-frame drain, cancellation/verification revocation, missing pack and Close concurrent with a blocked borrow. The concurrency test verifies submission remains possible during decode, Close revokes metadata before waiting, and application scratch is erased before Close returns. It does not measure a physical Stop deadline or vendor feature-buffer erasure.

Reproduce with the [runtime README](../../packages/wake-runtime/README.md) and [recorded results](../../packages/wake-runtime/tests/android-results.json). The standalone host-JVM harness batches three synthetic 20 ms frames with a deterministic receive clock and independently checks queued controller activation/Stop. Normal app tests run separately after evaluation; no evaluation assets are packaged. This is host transport evidence, not live recognition or Android device evidence.

VC-TURN-02 remains partial. Capture wiring, native runtime packaging/loading, production model-pack trust/selection/lifetime/attachment, physical microphone/routes/noise/latency and vendor retention/distribution evidence remain open before ASR. Unrelated `S02_REVIEW.md` edits are preserved and excluded. Stop for Gemju Sherpa review of this checkpoint.
