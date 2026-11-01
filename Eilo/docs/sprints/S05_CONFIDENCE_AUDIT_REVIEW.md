# S05 confidence audit v2 — selected criteria and implementation

Gemju Sherpa selected the proposed software confidence-audit criteria on 2026-10-30. This review freezes the decision and a pure, closed-schema acceptance calculator. It does not run inference, fit mappings, open the sealed audit, authorize a confidence threshold, activate ordinary speech, or change device/release support.

This is preparation under stable task **VC-TURN-10 — ASR quality trial**. It does not complete that task's corpus scoring, quality review or any physical microphone acceptance.

## Frozen decision

- Reuse only the already approved local Common Voice 26.0 Australian English archive and already approved iOS score paths.
- Select 600 previously unexposed train-split utterances: 200 development, 200 validation, and 200 sealed audit. Enforce disjoint provided client IDs and normalized utterances across all phases and every prior evaluated cohort. Provided IDs are opaque partition keys, not verified identities. Abort rather than relax the exclusions if fewer than 600 valid cases remain.
- Freeze the selected source/audio hashes, exact preprocessing recipe, selection code and protocol before model inference. Keep source IDs, references, audio, hypotheses and fitted knots under ignored `.local`; publish only aggregate results and checksums.
- Fit separate tie-grouped weighted PAVA mappings for `GREEDY_PREBIAS_MEAN_V1` and `SELF_DRAFT_PREBIAS_MEAN_V1` on development labels only. Use normalized exact transcription as the label and the fixed mapped cutoff 0.85. Do not refit, tune the cutoff, transfer across sources/platforms, or qualify model-training overlap (unknown).
- Validation requires exactly 200 attempts per source, at least 30% accepted coverage using all 200 attempts as the denominator, and a two-sided 95% Wilson lower bound of at least 0.85 for exact-transcription accuracy among accepted cases. Unavailable outputs remain unaccepted attempts.
- Open the sealed audit only after both validation sources pass and the mapping hashes are frozen. Evaluate once with the frozen mappings and identical criteria. A validation failure leaves the audit unopened; an audit failure is retained without a refit or threshold change.

The Wilson bound is deliberately conservative for this sample size: at exactly 60 accepted cases, at least 57 must be exact for the lower endpoint to reach 0.85. Passing the software audit would still not authorize production confidence, change the existing recognition policy, establish native calibration, clear physical/network/privacy gates, enable persistent memory, or lift S08/release HOLD.

## Implementation and current execution state

`packages/asr-calibration/audit-v2-protocol.json` freezes sample counts, sources, exclusions, label, fit and acceptance rules. `audit_v2.py` computes the specified interval and fails closed on incomplete cohorts, unavailable-score denominator manipulation, unexpected source sets and malformed inputs. `select_audit_v2.py` froze 600 private clips with FFmpeg 9.0.2: 200 development, 200 validation and 200 sealed-audit cases. Cross-phase speaker and normalized-text overlap are both zero; source IDs, audio and transcripts remain in ignored `.local`. `freeze_selection_v2.py` verifies the private manifests and emits a create-only public file containing only manifest/archive/receipt/code/decoder hashes and fixed protocol gates. That hash-only selection freeze must be committed before inference. `evaluate_validation_v2.py` fits development mappings, freezes only their hashes, verifies the exact committed mapping-freeze blob, binds private attempts to validation-manifest order, derives normalized exact-match labels locally and emits aggregate counts only. It does not run inference or write per-case data. The sealed-audit evaluator remains deliberately unavailable and rejects `SEALED_AUDIT` outright; opening that stage still requires both validation sources to pass and the frozen mapping hashes to match. No model inference has run; validation remains `NOT_RUN`. Unit tests use synthetic rows/counts only.

The local metadata preflight reproduced 52,834 eligible train rows and 754 eligible provided client IDs after excluding the 120 previously evaluated cases. FFmpeg is now installed with user approval; a probe decoded an archived MP3 to mono 16 kHz PCM successfully. Its binary SHA-256 is recorded in each local phase manifest. Cohort selection and preprocessing pins were verified after conversion. The 600-case inventory and three manifests remain ignored local data; the public hash-only selection freeze is committed before any inference. Separately, on 2026-10-30, `xcrun simctl list devices booted --json` could not connect to CoreSimulatorService and reported that no simulator runtime was available under the selected Xcode developer directory. No data/model inference, physical-device access, radio observation or destructive command was performed. Validation and sealed audit remain `NOT_RUN` and no qualification is claimed.

## Reproduction

```sh
cd Eilo/packages/asr-calibration
python3 -m unittest test_audit_v2.py
python3 -O -m unittest test_audit_v2.py
```
