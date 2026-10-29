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

## PR #106 CI download recovery

The original push Android job failed twice reading the pinned React Native 0.87.1 release AAR from Maven Central. The corresponding PR job passed. The push iOS retry exhausted its 40-minute job budget while a CocoaPods tarball download remained at about 2 MB for over 25 minutes; Ruby gem installation itself completed. No ASR test failed.

CI now separates Android external classpath preparation from the unchanged assembleDebug, assembleRelease and testDebugUnitTest gate. Preparation retains the existing dependency declarations/repositories and uses Gradle HTTP connection/read limits of 30/60 seconds. CocoaPods still uses the deployment lock and the existing checksum verification. Each preparation command has at most three eight-minute attempts, retaining completed cache entries. Timeout and cancellation stop its process group, including stalled downloader children. Builds and tests are never retried by this helper. Android/iOS job budgets become 45/50 minutes to accommodate bounded setup plus the full original build/test gates. This is a finite recovery allowance, not a successful-download guarantee.

Six process-level regressions pass in normal and optimized Python: retry with retained progress, failure propagation, single execution on success, timeout child cleanup, cancellation cleanup, and locked dependency-only commands. The real Android preparation task also passes against existing caches in offline mode, including React Native included-build and Android artifact variant handling. Hosted checks on the updated exact head remain mandatory before merge.
