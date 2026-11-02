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

`packages/asr-calibration/audit-v2-protocol.json` freezes sample counts, sources, exclusions, label, fit and acceptance rules. `audit_v2.py` computes the specified interval and fails closed on incomplete cohorts, unavailable-score denominator manipulation, unexpected source sets and malformed inputs. `select_audit_v2.py` froze 600 private clips with FFmpeg 9.0.2: 200 development, 200 validation and 200 sealed-audit cases. Cross-phase speaker and normalized-text overlap are both zero; source IDs, audio and transcripts remain in ignored `.local`. `freeze_selection_v2.py` verifies the private manifests and emits a create-only public file containing only manifest/archive/receipt/code/decoder hashes and fixed protocol gates. That hash-only selection freeze was committed before inference. `run_development_v2.py` is a create-only, development-only runner: it checks the exact committed selection and runner blobs, pinned iOS simulator scorer/runtime object/model/source hashes, and an already booted simulator before writing its start marker. It stores transcripts and raw attempts only under ignored `.local`, preserves unavailable outputs in each fixed 200-case denominator, and cannot target validation or the sealed audit. The completed run attempted all 200 development cases with zero collector errors and 199 available scores per source. `evaluate_validation_v2.py` fits mappings only from development labels, freezes only their hashes, verifies the exact committed mapping-freeze blob, binds private attempts to validation-manifest order, derives normalized exact-match labels locally and emits aggregate counts only. The development mapping hashes have been frozen in `mapping-freeze-v2.json` before validation. `run_validation_v2.py` adds a separate create-only validation runner requiring the committed mapping freeze; it is hard-bound to the validation phase and keeps per-case rows private. The sealed-audit evaluator remains deliberately unavailable and rejects `SEALED_AUDIT` outright; opening that stage still requires both validation sources to pass and the frozen mapping hashes to match. Validation remains `NOT_RUN`; no software audit qualification is claimed. Unit tests use synthetic rows/counts only.

The local metadata preflight reproduced 52,834 eligible train rows and 754 eligible provided client IDs after excluding the 120 previously evaluated cases. FFmpeg is installed with user approval; a probe decoded an archived MP3 to mono 16 kHz PCM successfully. Its binary SHA-256 is recorded in each local phase manifest. Cohort selection and preprocessing pins were verified after conversion. The 600-case inventory and three manifests remain ignored local data; the public hash-only selection freeze is committed before inference. With user approval, Xcode downloaded and installed the iOS 27.1 simulator runtime. CoreSimulator services required elevated access in this environment; an iPhone Duo simulator was booted and the pinned runner completed the one-time 200-case development pass. The private attempts and execution receipt remain ignored local data, and development mappings were fitted from those attempts and reduced to a hash-only public freeze before validation. No physical-device access or radio observation was performed. Validation and sealed audit remain `NOT_RUN`; no qualification is claimed.

## Reproduction

```sh
cd Eilo/packages/asr-calibration
python3 -m unittest test_audit_v2.py
python3 -O -m unittest test_audit_v2.py
python3 -m unittest test_run_development_v2.py
python3 -O -m unittest test_run_development_v2.py
python3 -m unittest test_run_validation_v2.py
python3 -O -m unittest test_run_validation_v2.py
```

The private runner requires the ignored development selection at `.local/asr-calibration-audit-v2/selection-private.json`, the already-built and pinned iOS scorer/runtime files at `.local/asr-ios-corpus/run-v1/`, an existing Moonshine model directory whose eight files match the public provenance hashes (the current physical-trial assets were verified), and a booted iOS simulator. Invoke it only after the commit containing `selection-freeze-v2.json` and the exact runner source are on the current history. It writes a create-only private start marker and attempts file; a started run must not be repeated or overwritten.
