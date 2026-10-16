# VC-TURN-04/05 — bounded 48 kHz capture route conversion

PR67 merged at 239f77a; all eight checks PASS. Separate converter, capture integration and
validation branches feed sprint/native-48k-route-conversion for one review PR. Main merge
remains for human review; physical acceptance remains separate.

## Streaming converter

Worker-confined StreamingRateConverter supports mono Float32 at 16000 or 48000 Hz. 16 kHz
is bit-preserving. 48 kHz uses 193 pinned Float32 Hamming-windowed sinc taps, cutoff 7000 Hz,
unity DC, and decimation by three. The causal filter has 96 input samples (2 ms) of linear-phase
delay. Zero startup and no EOF flush produce exactly floor(total input/3) output samples;
remaining one/two input samples are discarded on close. FIR overshoot saturates to [-1,1].
History/phase survives arbitrary chunks but is erased on close/failure; unsupported rates,
oversized/nonfinite/out-of-range input and consumer failure close permanently. No converter
runs on a recorder callback. No resampling library/download or platform API assumptions added.

Coefficient generator/check records its recipe and Float32-LE digest in vad-runtime/tests/rate-filter.json.
It verifies <=0.1 dB passband error at 0..6000 Hz and >=50 dB rejection at 8000..24000 Hz on a
25-Hz grid; checks remain active under optimized Python. Both platform tests additionally verify
streamed 1 kHz/10 kHz tones, chunk invariance, phase/count, bit-preserving bypass and failures.
Converter checks: 276 Swift/329 Android tests PASS; Android lint/Debug/Release compile PASS;
normal same iPhone18 Pro simulator build/install/three ten-second launches PASS before commit.

## Capture integration

VAD capture slots accept fixed 16/48 kHz sources and configure their transport accordingly.
The raw queue remains four <=100 ms frames (at most 19200 raw samples at 48 kHz), with the
existing <250 ms age limit. Conversion runs only on the inference worker, before normalized
VAD windows and optional ASR audio ownership. Raw ring history and conversion scratch close on
worker cleanup. Default normal application entry points still attach no model/runtime.

All endpoint counts and lastChunkConsumed remain in the normalized 16 kHz clock. A caller must
not interpret these as original capture indices; the filter has an explicit delay and a completed
endpoint discards the remaining normalized/raw callback suffix. Stream rate changes fail closed;
this task does not migrate a running turn between routes. Android's recorder still requests 16 kHz;
iOS uses the observed mono channel at its supported actual rate without forcing session format.
Capture integration checks: 280 Swift/333 Android tests PASS, compiler/lint and same normal
simulator build/install/three ten-second launches PASS. Quiet/EOF/tail/count, raw queue overflow,
rate mismatch and 48 kHz slot-to-ASR exact-prefix/confidence tests pass.

## Joined native regression and final validation

The three tasks are complete for one sprint PR. Actual approved-model iOS simulator and macOS
host JVM/JNI regression opens/closes six streams and makes 318 calls per platform. The new fixed
48 kHz case consumes 240000 raw samples, produces exactly 80000 normalized samples, ends NO_SPEECH,
opens ASR zero times and clears queued/owned audio. Existing 16 kHz/short EOF/Stop/cleanup cases
still pass. Positive ASR integration remains scripted; no acoustic accuracy is inferred.

Final local checks PASS: 280 Swift and 333 Android tests (zero failures/errors/skips), Android
lint/Debug/Release packaging, normal same iPhone18 Pro simulator build/install/three ten-second
launches, workspace lint/typecheck and nine mobile/33 contract tests, 56 dataset and 47 feasibility
tests normal/optimized, coefficient checks normal/optimized, native sanitizer contracts and CI
simulator/wake/model-source fixtures. Existing Jest act warnings remain; no suppression added.
Source/model/binary/filter hashes and clock semantics are recorded in vad-runtime/tests. Native
regression updates the existing asr-handoff-native-regression.json as the current shared pipeline
proof; prior runs remain in Git history. Normal artifacts include no evaluation model/runtime
activation. No downloads, package installs, microphone requests or production overrides occurred.
Feasibility source pins remain valid and all existing HOLD/physical/privacy gates are unchanged.

## Gates

This supports only 16/48 kHz mono. 44.1 kHz, other rates, route changes, channel/downmix policy,
physical quality/latency/battery and clock/route calibration remain unverified. Sample metadata
is in the normalized 16 kHz clock; it is not a raw capture-prefix index. Production remains
NOT_ENABLED, physical gates NOT_RUN, S08 HOLD and persistent memory denied. Preserve personal edits.
