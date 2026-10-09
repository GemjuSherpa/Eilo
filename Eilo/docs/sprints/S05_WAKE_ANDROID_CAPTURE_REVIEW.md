# S05 Android capture-to-wake integration review

VC-TURN-02 / F03 / A02. Gemju Sherpa reviewed and merged PR #33; fetched main `d6e29ed`. Branches: `task/s05-vc-turn-02-android-capture` → `sprint/s05-wake-android-capture` → main PR awaiting review.

Previously Android capture retained bounded standby audio but did not feed the reviewed wake queue. `ForegroundCapture` now supports native attachment of an independently verified delivery built on a native inference worker. Attachment requires this controller's current standby token, matching delivery token, fixed 16 kHz capture rate, an open eligible capture and no existing binding. Capture-run and lifecycle-epoch checks reject an attachment across Stop/clear/cancellation races. Rejected candidates remain the caller's responsibility to close; transferring one detector/delivery to multiple capture instances is unsupported.

Each native nonblocking read submits its bounded PCM16 prefix before erasing the reused read buffer. The continuous native capture worker drains outside the capture monitor, then applies metadata after delivery releases its locks. A matching live detector failure reaches existing capture failure handling. Old or detached bindings cannot fail a replacement. Generation cancellation closes and detaches the delivery on the next drain. `cancelWork`, context clearing, capture release and abandoned-run cleanup revoke/close attached delivery. Stop waits for a synchronous borrowed decode without holding the capture monitor; the decoder never needs the controller lock to finish. Application buffers are erased before Stop returns.

The native attachment API takes an already constructed delivery. Construction must happen on a separate native inference worker, because enqueueing behind the continuous capture loop would starve it. No default app call, automatic JNI loading, model-readiness bypass, microphone permission change, JS PCM or ASR is introduced. Production model-pack attachment remains a separate gate.

| Check before commit | Actual result |
|---|---|
| Android Kotlin compiler / normal JUnit / lint | PASS: 105 tests, zero failures/errors/skips |
| Android Debug and Release builds | BUILD SUCCESSFUL |
| Capture integration tests | PASS: actual capture loop with synthetic device/backend; wrong controller/token/rate and duplicate attachment rejected; wake transitions to Capturing; canceled generation closes stream; Stop during blocked decode completes without deadlock or late activation; detach/reattach, backend failure cleanup and late failure rejection for a replacement pass |
| Same iPhone 18 Pro / iOS 27.0 simulator | Debug BUILD SUCCEEDED; installed app passed three fresh ten-second launches |
| Real JNI synthetic acoustic evidence | Reviewed PR #33 evidence retained; not rerun in this capture-only checkpoint |
| Android device/emulator, AudioRecord microphone, physical timing/routes | NOT RUN |
| Staged diff / secret scan | PASS before commit |
| Hosted checks | Pending at PR publication |

The four new integration tests use a real serial Java executor running `ForegroundCapture`, a synthetic 16 kHz device and scripted keyword engine. They verify actual capture buffer erasure and controller lifecycle behavior; they do not establish acoustic quality, Android hardware operation or a physical Stop-latency target. Eight reviewed queue tests remain in the normal suite. The real Kotlin/JNI queue evaluation and four ABI links were established in PR #33 and are unchanged here.

Reproduce Android checks from the repository root with installed JDK 17/SDK and cached dependencies:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
ANDROID_HOME=/Users/gemju/Library/Android/sdk \
Eilo/apps/mobile/android/gradlew -p Eilo/apps/mobile/android \
  :app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug \
  :app:assembleDebug :app:assembleRelease --offline --max-workers=2
```

Remaining: local native runtime packaging/loading, verified production pack trust/selection/lifetime and worker-side attachment, physical microphone/routes/noise/latency, vendor buffer retention and distribution evidence. No full voice conversation or ASR success is claimed; VC-TURN-02 remains partial. Unrelated `S02_REVIEW.md` changes remain excluded. Stop for Gemju Sherpa review.
