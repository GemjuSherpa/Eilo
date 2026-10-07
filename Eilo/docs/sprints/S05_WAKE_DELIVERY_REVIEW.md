# S05 native iOS wake delivery review

VC-TURN-02 / F03 / A02. Reviewed base: PR #30 merge `cdef969`. Branches: `task/s05-vc-turn-02-ios-delivery` → `sprint/s05-wake-capture` → main PR awaiting Gemju Sherpa review.

Previously the iOS capture tap retained/erased PCM but had no worker delivery path to the keyword detector. The new native queue preallocates four <=100 ms frames plus bounded worker scratch, preserves order and rejects discontinuities. Frames older than 250 ms, overflow, invalid samples/rates or receive-clock regression revoke delivery before reporting one worker failure. The callback copies only; the decoder runs on the existing capture worker. Returned wake metadata enters the controller after decoder locks end, with both detector/delivery leases checked inside controller serialization.

`IOSCaptureEffects` now owns one per-capture slot, submits the first native Float channel before callback erasure, and drains on the 50 ms worker timer. Native attachment initializes an exclusively owned verified detector/current token on that worker; late attachment after Stop is rejected. Cancel/volatile cleanup detaches and erases delivery; Stop closes the slot and waits for borrowed decode before erasing scratch/destroying the handle. The app still uses missing-model readiness and never calls attachment by default. No consent change, automatic capture, JS PCM, ASR, persistence, network inference or paid service is added.

| Check before commit | Result |
|---|---|
| `swift test --package-path Eilo/packages/native-test-seam` | PASS: 93 XCTest tests, nine new delivery tests covering callback/worker separation, FIFO ownership/erasure, overflow, invalid input, expiry/regression, event revocation, Stop/privacy, late attachment, detach/restart and in-flight decode race |
| `python3 Eilo/packages/wake-runtime/check_ios.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8` | PASS: pinned integrity checks, C++ device/simulator and Swift iOS compilation; all 28 frozen synthetic entries match direct and queued real-decoder results |
| Acoustic/transport acceptance | 11 wake entries detected, zero activations across 15 nonwake entries; two diagnostics excluded; 24 unique WAVs from one installed voice. Scripted receive clock and synthetic controller; no audio device |
| Python integrity tests, normal and `-O` | PASS: four tests in each mode |
| Local unsigned Debug app | BUILD SUCCEEDED on the same iPhone 18 Pro / iOS 27.0 simulator; actual capture tap/worker code compiled |
| Installed app launch verification | PASS: three fresh ten-second launches after the final build |
| Hosted checks | Pending at PR publication |

Reproduction: [runtime README](../../packages/wake-runtime/README.md); [recorded direct/queued results](../../packages/wake-runtime/tests/ios-results.json). Standard simulator app is left running. Binaries/models/WAVs remain local and ignored. Unrelated `S02_REVIEW.md` changes are excluded.

This checkpoint remains partial: production model-pack selection/trust/lifetime, Android vendor binding/delivery and physical microphone/route/noise/performance evidence are open. No real capture success or full ASR result is claimed. Stop can wait for synchronous vendor decode; its physical latency and vendor feature-buffer erasure are unverified. Verification callbacks must not acquire controller/capture locks; returned metadata is applied after processing locks are released. Next checkpoint: Android native vendor binding, followed by verified pack attachment and microphone validation before ASR.
