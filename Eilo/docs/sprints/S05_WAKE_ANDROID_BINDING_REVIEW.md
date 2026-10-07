# S05 Android wake binding review

VC-TURN-02 / F03 / A02. Gemju Sherpa reviewed and merged PR #31; verified base main `9f00bf6`. Branches: `task/s05-vc-turn-02-android-binding` → `sprint/s05-wake-android-binding` → main PR awaiting review.

Previously Kotlin had only a keyword-stream port and scripted fixtures. This checkpoint adds an actual Kotlin/C ABI JNI binding with a fail-closed unavailable default, independently verified native paths, fixed keyword-only results, serialized borrow/close and revocation on bad input/rate/native/verification failures. JNI uses non-reusable opaque IDs and preallocated bounded native scratch, copies only the borrowed array prefix, erases its own copy after processing and rejects stale handles. It adds no automatic library loading, microphone wiring, model readiness, ASR, JS PCM, persistence or paid service.

The official pinned Android archive supplies matching C API and ONNX Runtime libraries. The offline verifier checks publisher archive SHA256, extracted files, matching header/host runtime, models and frozen fixtures, then cross-links JNI for all four Android ABIs. Its standalone host-JVM harness uses actual Kotlin binding/detector/controller with explicit synthetic capture/readiness, real host vendor decoding, Stop checks and invalid/stale JNI IDs. Generated libraries, models, WAVs and Gradle init script remain ignored. The app does not package the evaluation library or assets.

| Check before commit | Actual result |
|---|---|
| Android Kotlin compile / normal JUnit / lint | PASS: 93 tests, seven new binding/lifetime/error/Stop tests; zero failures/errors/skips |
| Android Debug and Release app packaging | BUILD SUCCESSFUL; normal app without evaluation native assets |
| NDK C++17 `-Wall -Wextra -Werror`, no undefined references | PASS: API 26 `arm64-v8a`, `armeabi-v7a`, `x86`, `x86_64` shared-library links |
| Explicit real Kotlin/JNI host-JVM evaluation | PASS: all 28 frozen entries; 11 wake, zero activations across 15 nonwake, two excluded diagnostics, 24 unique WAVs; native/controller Stop and invalid/stale handles pass |
| Python integrity/report regressions, normal and `-O` | PASS: five tests in each mode; rejects tampering, missing assets, one-sided fixtures and deceptive result reports |
| Same iPhone 18 Pro / iOS 27.0 simulator Debug app | BUILD SUCCEEDED; installed app passed three fresh ten-second launches |
| Android device/emulator decoding and microphone | NOT RUN: no connected Android test target; no microphone used |
| Staged diff / secret scan | PASS before commit |
| Hosted checks | Pending at PR publication |

Reproduce using the [runtime README](../../packages/wake-runtime/README.md); inspect [binding results](../../packages/wake-runtime/tests/android-results.json) and [provenance](../../packages/wake-runtime/android-provenance.json). The first runner attempts failed because the selected bundled JBR lacked JNI headers and the harness used desktop audio APIs outside Android's compile surface. Both were corrected using the installed full JDK 17 and a bounded WAV parser; the final real-decoder run passes. An initial Gradle attempt lacked the SDK environment; final checks explicitly select the installed SDK. No dependency or acceptance gate was disabled.

Remaining: Android local runtime packaging/loading and capture delivery, production pack trust/selection/lifetime/attachment, physical microphone/routes/noise/latency, vendor buffer erasure and license/distribution closure. Verification callbacks must not acquire capture/controller locks; Stop can wait for synchronous decode. No Android device, physical accuracy or full voice-conversation/ASR success is claimed. Parent VC-TURN-02 remains partial. Next small checkpoint: Android bounded capture-to-worker delivery. Unrelated `S02_REVIEW.md` changes remain excluded.
