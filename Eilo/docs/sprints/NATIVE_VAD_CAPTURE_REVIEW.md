# VC-TURN-04 — native VAD capture integration

Prerequisite PR65 is merged at 1f41bfa; all eight checks passed. This sprint uses separate task
branches merged into sprint/native-vad-capture-integration and one final PR for review.
No main merge is authorized. VC-TURN-03/04 production and physical acceptance remain partial.

## Bounded capture transport

Capture callbacks copy at most four frames of <=1600 samples (100 ms at 16 kHz), schedule one
coalesced job and never invoke native inference or retain a borrowed buffer. Queue overflow,
invalid data/rate, regressing clock or >=250 ms queue age revoke the transport and erase queued
PCM. Android PCM16 uses exact signed /32768 conversion. Only a dedicated serial native worker
opens/processes/closes the VAD stream and owns its scratch. Stop revokes and clears the queue
immediately and schedules cleanup even without another frame; in-flight scratch clears when the
borrowed synchronous inference returns. No inference wait occurs under capture/controller locks.

The callback carries only result/sample metadata and a recheckable lease; endpoint total/prefix
accounting excludes the trailing callback suffix. EOF is ordered after queued audio and uses the
actual short tail. No transcript, ASR confidence, speech readiness or production trust is inferred.
The worker executor must remain available for the entire binding lifetime and enqueue serially,
never run tasks inline on the recorder. Supported PCM rate is exactly 16 kHz; unsupported routes
fail closed. No route resampler or performance suitability is claimed.

Transport checks: 252 Swift and 303 Android tests PASS; Android lint/Debug and Release compilation
PASS using existing dependencies. Normal iPhone18 Pro simulator build/install and three fresh
10-second launches precede the task commit. Shared dependency resolution uses the previously
created ignored Metro override, with no package installation or committed configuration change.

## Acceptance boundary

Physical voice, Android ART/device capture, route changes, latency, battery, screen-lock/background
and endurance remain NOT_RUN. Production remains NOT_ENABLED; S08 remains HOLD. Human-labelled
VAD accuracy remains blocked on annotations. The original three personal edits are preserved.
