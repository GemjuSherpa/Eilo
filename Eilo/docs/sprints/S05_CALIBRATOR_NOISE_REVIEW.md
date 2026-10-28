# S05 frozen calibrator noise review

The frozen development calibrator from PR #105 was applied unchanged to 90 deterministic MUSAN mixtures: the same 30 known-speaker test utterances at 20, 10 and 0 dB SNR. These correlated variants are not a new independent holdout. The total clean corpus examined remains 120 clips. No model refit or threshold fitting occurred.

Protocol and execution code were committed at `fd5a20dc2495675f93e1b22bf54dfb09032ce352` before inference. Existing approved local Common Voice 26 Australian English and twelve public-domain MUSAN noise files were reused; no downloads, new dependencies, capture, device access or ordinary-app runtime changes occurred. Three isolated Android native collector builds produced the 90 variant observations and rejected all four invalid inputs per condition. Private source/model hashes were checked before and after execution. Full native provenance and aggregate results are in `noise-results.json`; transcripts, audio, case scores and fitted knots remain local.

At the fixed diagnostic cutoff of 0.85:

| Condition | Scores available / 30 | Greedy mapped accepted / errors | Draft mapped accepted / errors | Available-case WER |
| --- | --- | --- | --- | --- |
| Clean (existing PR #105) | 29 | 20 / 0 | 20 / 0 | 0.0424 |
| 20 dB | 29 | 16 / 2 | 15 / 2 | 0.0601 |
| 10 dB | 29 | 14 / 1 | 13 / 1 | 0.0813 |
| 0 dB | 28 | 3 / 0 | 3 / 0 | 0.1502 |

Both score paths accept incorrect transcriptions under noise. At 0 dB the apparent zero accepted errors comes with only 10% coverage. Brier scores improved relative to raw scores within this sample, but that does not establish robust calibration, a safe threshold, unseen-speaker performance or zero risk. Endpoint clamping follows the existing frozen model; no failures were replaced or used to refit it.

Validation: 20 unit/contract tests pass in normal and optimized Python. CI validates immutable source/model/baseline pins, denominators, approved noise inventory, aggregate metrics and forbidden qualification changes without accessing corpora or models. Only JSON/HTML aggregate summaries are uploaded for seven days. The full offline workflow and hosted application gates must pass before merge.

Production confidence remains NOT_ENABLED; native calibration NOT_ESTABLISHED; threshold authorization NOT_GRANTED. Physical acceptance remains NOT_RUN / OPEN, S08 and release HOLD, persistent memory DISABLED. This is diagnostic evidence, not a release gate pass.
