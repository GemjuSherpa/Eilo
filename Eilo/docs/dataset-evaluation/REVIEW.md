# VC-DATA evaluation review

Status: implementation awaiting independent review. Public-corpus and physical acceptance
are separate. Additive VC-DATA-01–05 IDs do not replace the existing 175 stable tracker IDs.
Scope maps to S08's missing acoustic corpus prerequisite; it does not close S08 or its gates.

| Task | Branch / PR | Implementation | Evidence |
|---|---|---|---|
| VC-DATA-01 | task/vc-data-01-manifests / #52 | licensing/access registry, streaming SHA receipts | 4 normal/optimized tests |
| VC-DATA-02 | task/vc-data-02-preprocessing / #53 | deterministic held-out PCM/index | 9 cumulative tests |
| VC-DATA-03 | task/vc-data-03-benchmarks / #54 | corpus-bound adapter/scorer | 15 cumulative tests |
| VC-DATA-04 | task/vc-data-04-noise-regression / #55 | seeded noise/SNR and slice regression | 19 cumulative tests |
| VC-DATA-05 | task/vc-data-05-reports-ci / pending | JSON/HTML, CI, local extraction/native protocol integration | 27 cumulative tests; actual 30-clip native ASR trial |

PRs are stacked in dependency order to expose individual task diffs. Review #52 against main,
then #53–55 against preceding task branches; retarget dependencies after reviewed merges.
No task has been approved or merged by this agent. Main was fetched at f294fed (PR #51
already merged). #51 final head CI38506830941 SUCCESS; no formal reviews were recorded.
Original checkout's personal Xcode/plist/S02 edits are untouched in a separate filesystem tree.
No mobile app source, entitlement, model-readiness policy or physical evidence is changed.
Changed-app simulator build requirement is inapplicable to this desktop Python package;
no new simulator/device success is claimed. Hosted foundation checks run on these PRs.

## Checks

27 focused tests pass under ordinary and optimized Python 3.12. Compilation, registry validation,
synthetic JSON/HTML smoke, diff checks and gitleaks scans pass. Cases cover integrity tampering,
path escapes, unsafe archives, split selection, PCM format/rates, adapter binary/config pins,
no truth labels in adapter request, WER/CER/VAD arithmetic, missing/mismatched/NaN predictions,
noise repeatability/SNR/headroom, incompatible/forged regression reports and HTML escaping.
CI downloads no corpus/model and uploads only explicitly allowlisted synthetic summaries.
The pinned checkout and upload-artifact actions follow existing public hosted-runner policy.

## Initial real-corpus diagnostic

User approved public MUSAN/Speech Commands downloads on 14 October 2026. Speech Commands 0.02
archive size2428923189, local SHA-256 af14739ee7dc311471de98f5f9d2c9191b18aedfe957f4a6ff791c709868ff58;
archive LICENSE identifies Attribution4.0International. This hash is LOCAL_OBSERVED, not a
publisher-authentication claim. Audio/receipts/subsets/results stay in ignored `.local/datasets`.
Thirty deterministic official-test clips (seed0) passed native macOS ARM64 Moonshine v0.1.5
execution using already-provisioned exact-hash vendor/model assets. No new model downloaded.
WER10/30=33.33%; CER34/133=25.56%; ASR-derived command accuracy27/30=90%. The subset has21unknown
words and9target words: target-only6/9=66.67%, observed-label balanced64.29%. These are small,
imbalanced desktop diagnostics, not full corpus, native command-controller or physical passes.
RTF0.564 includes process startup and verification of vendor/model files per clip; no device
latency conclusion. Existing host runner checks finalization/closed-input behavior per file.
MUSAN download/noise evaluation is still in progress at this initial review checkpoint.
Native positive/negative VAD model evaluation is NOT_RUN; reviewed positive VAD annotations
and native adapter are absent. Public utterance transcripts are not endpoint annotations.

## Remaining access and gates

Common Voice English release remains UNSELECTED. User must provide/authorize MDC account
access and accept the selected dataset's terms; no account login or terms acceptance occurred.
Recheck its license/card/datasheet, pin release, then download through the official platform.
MDC CC0 computational licensing does not grant permission to mirror the downloaded dataset.
CV MP3 decoding requires a separately provisioned hash-pinned local decoder; none installed.
No large dataset, transcript, speaker identifier, native binary or model is committed/uploaded.
Physical capture/interruption/endurance/standby/screen-off/device latency remain NOT_RUN.
Screen-off policy is unchanged. Production model trust, acoustic endpoint annotations and
native VAD wiring remain prerequisites, not scoring failures. No supported configuration or
persistent-memory permission is inferred. No paid service, deployment or main merge.
