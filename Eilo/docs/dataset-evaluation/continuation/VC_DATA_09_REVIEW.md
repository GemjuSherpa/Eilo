# VC-DATA-09 — paired Common Voice noise evidence

PR61 is reviewed/merged at main 7d7182f; all eight push/PR CI checks passed. This separate task
adds paired clean/noisy ASR verification and aggregate reporting, using the already approved
local Common Voice 26 Australian English subset, MUSAN free-sound component pool and existing
Moonshine adapter/runtime. No downloads, package installs, microphone access or app activation.

A fresh native clean 30-clip run and 90 seeded noisy variants completed. Each SNR has the same
30 clips and 243 reference words; all 90 mixed PCM hashes were independently reproduced from
the frozen inputs and recipe before report generation. The same exact adapter, model, config,
normalization and scoring were required across both runs. Reports bind case IDs, reference
counts, durations and slices. Actual metrics:

| Condition | Word errors / reference words | WER | CER |
| --- | --- | --- | --- |
| Clean | 60 / 243 | 24.69% | 14.14% |
| 20 dB | 86 / 243 | 35.39% | 20.97% |
| 10 dB | 93 / 243 | 38.27% | 22.72% |
| 0 dB | 141 / 243 | 58.02% | 37.57% |

These tiny English-subset diagnostics do not establish product quality, accent/language coverage,
physical microphone behavior or a release gate. Status MEASURED_DIAGNOSTIC, acceptance
NOT_ASSESSED. No threshold/model changes hide degradation. Noise-category labels are not VAD
gold; reviewed time-aligned annotations remain unavailable locally. Prior unscored VAD reports
and original audio/reference evidence remain intact and ignored. Only aggregate JSON and hashes
are committed, not transcripts, clip/speaker IDs, audio, generated packs or local paths.

Validation: 56 tests in normal and optimized Python pass; compile, registry and synthetic smoke
pass. New regressions reject missing/duplicate pairs, changed truth/pool/recipe/adapter/scoring,
changed PCM, and consistently rehashed PCM that does not reproduce the recipe. Tests verify
hand-computed deltas, synthetic-adapter rejection on public evidence, privacy, no-overwrite and physical NOT_RUN gates. Existing CI runs these
synthetic cases without models/downloads. No app code changed, so no local app rebuild is needed;
hosted native checks are separately reported. Original three user edits retain their exact hash.

Task branch task/vc-data-09-paired-noise-evidence merges into sprint/asr-noise-evidence for its
PR to main. No automatic main merge or history rewrite. Physical gates remain NOT_RUN,
production NOT_ENABLED and S08 feasibility remains on hold. Actual VAD scoring needs a human
reviewer's exported labels; native mobile/session/trust/offline-voice and device trials remain open.
