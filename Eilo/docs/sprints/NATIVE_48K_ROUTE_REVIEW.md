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

## Gates

This supports only 16/48 kHz mono. 44.1 kHz, other rates, route changes, channel/downmix policy,
physical quality/latency/battery and clock/route calibration remain unverified. Sample metadata
is in the normalized 16 kHz clock; it is not a raw capture-prefix index. Production remains
NOT_ENABLED, physical gates NOT_RUN, S08 HOLD and persistent memory denied. Preserve personal edits.
