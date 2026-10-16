# Signed speech capture installer — VC-TURN-04/05 / VC-PACK

PR69 merged at 81400a1 with all eight CI checks passing. This sprint completes the
capture-installer work described in NATIVE_SPEECH_PACK_REVIEW.md. Three task branches
feed sprint/signed-speech-capture-installer and one final PR; main merge requires review.

| Subtask | Branch | Result |
| --- | --- | --- |
| Pre-scheduling tickets and revocation hook | task/speech-capture-setup-tickets | Implemented and tested |
| Signed VAD/ASR installation and platform entry points | task/signed-speech-capture-installation | Implemented and tested |
| Capture integration, runtime regression and packaging evidence | task/speech-capture-installer-validation | Implemented and tested |

## Behavior and ownership

Previously the signed speech leases were independent primitives. Explicit capture setup now
mints a ticket before scheduling or reading model files. The ticket binds the exact capture
slot/context epoch, effects object, controller and generation token. Capture release, context
clearing, Stop, generation changes or another successful attachment reject stale tickets.
Final attachment rechecks identity/epoch/controller permission without replacing a newer binding.

SpeechCaptureInstaller runs on a dedicated serial inference worker. It resolves both exact
signed VAD and eight-file ASR selections and rechecks the ticket between expensive operations.
Wrong kinds, missing/untrusted/corrupt selections and stale setup return false without native
model creation. Rejected candidates revoke both leases. Successful attachment transfers both
leases into the capture permit; its joint checks remain disk-free. Model hashing, inference,
native destruction and joins never run under a capture/controller lock.

Stop/clear/release immediately revoke the permit and both leases, clear the transport queue,
and signal worker cleanup even when no further frame arrives. Normal completion keeps leases
valid through ASR finalization and the last controller check, then revokes them. A worker-only,
once-only terminal hook also releases ownership if the outcome is withheld. Stream destruction
continues to belong to the inference worker; lease close only revokes a capability.

IOSCaptureEffects.connectSpeech snapshots the current slot/run and creates the ticket before
its asynchronous inference job. ForegroundCapture.prepareSpeechSetup creates the corresponding
Android ticket for the caller to schedule SpeechCaptureInstaller on its serial inference worker.
These APIs are explicit native entry points; no normal app caller or production trust is added.
The changed iOS feasibility observation was reviewed and only its source checksum refreshed:
consent/readiness/background policy remains unchanged.

## Validation

- Full suites: 295 Swift and 349 Android tests; zero failures/errors/skips. Native compiler,
  Android lint and normal Debug/Release APK builds pass.
- ES256 synthetic packs exercise one complete scripted VAD→ASR turn, lazy model creation,
  exact selections, wrong kind/missing second pack, stale/reused tickets, detach during
  resolution, signed epoch replacement and Stop during VAD/ASR cleanup. Existing lease tests
  retain signature/hash/license/corruption and native creation/finalization coverage.
- Actual ForegroundCapture runs with a synthetic recorder and separate inference executor.
  Standby setup is denied; context clear rejects its pending ticket; a fresh ticket installs;
  copied frames run native interfaces on the inference worker and Stop closes that worker's
  stream. No microphone, Android ART or physical-device execution is inferred.
- Cached approved Silero VAD executes through signed lab-pack leases on iOS simulator and
  macOS JVM/JNI: six opens/closes and 318 model calls each; quiet 16/48 kHz, EOF, Stop,
  cleanup and epoch revocation pass. This regression exercises existing transport/lease paths;
  the new installer uses scripted VAD/ASR APIs in its tests. Real signed ASR weights and actual
  VAD through the new installer remain NOT_RUN, distinct from the tested signed primitives.
- Normal same iPhone18 Pro simulator build/install and three fresh ten-second launches pass
  before each of the three code-task commits (nine launches). Startup is not a voice trial.
- Workspace lint/typecheck, nine mobile/33 contract tests, 56 dataset and 47 feasibility tests
  in normal/optimized Python, all six reports, native sanitizer contracts, normal/optimized FIR
  verification and simulator/wake/model-source CI fixtures pass. Existing Jest act warnings
  remain without suppression.
- Normal APKs/iOS bundle contain no evaluated ONNX/ORT weights or ASR/VAD activation imports.
  Binary/source hashes are recorded in vad-runtime/tests/speech-capture-installer-results.json;
  shared actual runtime provenance is in asr-handoff-native-regression.json.

## Remaining parent gates

Physical voice/route/latency/battery/screen-off gates are NOT_RUN. Production is NOT_ENABLED,
trust/selections are NOT_CONFIGURED, S08 remains HOLD_PENDING_PHYSICAL_EVIDENCE and persistent
memory remains denied. Lab signing/license fixtures confer no production approval. Slots must
remain app-private and immutable, with epochs revoked before maintenance. No arbitrary external
file mutation detection, calibrated ASR confidence or full-duplex acoustic separation is claimed.

Next dependency-ready work is a real signed-ASR/installer evaluation and wake-to-question
alignment, followed by reviewed production trust/runtime/caller integration. Physical acceptance
still requires separately scoped device trials; no downloads, installs or microphone activation
were needed for this sprint. Original personal Xcode/plist/S02 edits are preserved exactly.
