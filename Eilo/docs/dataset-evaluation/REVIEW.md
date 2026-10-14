# VC-DATA public corpus evaluation review

Implementation and initial desktop evaluation are prepared for independent review. This
additive workstream addresses S08's missing acoustic corpus prerequisite without replacing
any of the175stable tracker IDs, closing S08, enabling production readiness or passing gates.

| Task | Separate branch / PR | Result |
|---|---|---|
| VC-DATA-01 | task/vc-data-01-manifests / [#52](https://github.com/GemjuSherpa/Eilo/pull/52) | license/access/version registry, stream SHA receipts;4initial tests |
| VC-DATA-02 | task/vc-data-02-preprocessing / [#53](https://github.com/GemjuSherpa/Eilo/pull/53) | deterministic official held-out PCM/index;9cumulative tests |
| VC-DATA-03 | task/vc-data-03-benchmarks / [#54](https://github.com/GemjuSherpa/Eilo/pull/54) | bounded adapter and ASR/VAD/command scoring;15cumulative tests |
| VC-DATA-04 | task/vc-data-04-noise-regression / [#55](https://github.com/GemjuSherpa/Eilo/pull/55) | seeded SNR/headroom and per-slice regression;19cumulative tests |
| VC-DATA-05 | task/vc-data-05-reports-ci / [#56](https://github.com/GemjuSherpa/Eilo/pull/56) | JSON/HTML, CI, extraction/native integration and final integrity/licensing refinements;34cumulative tests |

PRs are stacked in dependency order to expose individual task diffs. Review #52 against main,
then #53–56 against the preceding task branch; retarget after reviewed dependency merges.
No PR approval/main merge is performed by this agent. Integration fixes and actual downloaded
checksum/licensing evidence are included in #56; review the final stack as well as each diff.
Initial Python bytecode accidentally included in a local #52 commit was removed in an explicit
follow-up, with generated caches ignored. Final diffs contain no bytecode or audio.

## PR51, repository and validation

PR51 was already merged before this task at main f294fed9d0ec3129888ed8334136fae472e55438;
final head109edf7 CI38506830941 passed JavaScript, Android and iOS/history. No formal reviews
were recorded; no new approval was submitted to a closed PR under its author's identity.
A separate clone preserves original personal Xcode/plist/S02 edits. No mobile app source,
permissions, entitlements, screen-off policy, pack readiness or physical evidence is changed.
Changed-app simulator checks are inapplicable to this desktop package; no new device/startup
success is inferred. Hosted foundation checks separately build/test unchanged mobile code.

Final34focused tests pass in ordinary/optimized Python3.12; compile/registry, synthetic
JSON/HTML smoke, diff and gitleaks checks pass. Existing47voice-latency tests pass in both
modes, and existing voice-trial/ASR-quality evidence tests pass(2each). Default S08 decision
remains HOLD_PENDING_PHYSICAL_EVIDENCE, supported configurations empty, persistent memory
false. No private-plan tracker/acceptance artifacts are rewritten.

Tests include checksum tampering, existing-pin replacement, missing approvals, unsafe archives,
CV split overlap, deterministic selection/PCM rates/formats, pinned decoder/native config,
no truth in adapter requests, WER/CER/VAD arithmetic and partial frames, unknown-class
imbalance, missing/mismatched/NaN outputs, weak VAD label rejection, seeded SNR/headroom,
regression thresholds/slices and escaped privacy-reduced HTML. Real Apple MP3 repeat decoding
produced identical PCM. Native host checks finalization/closed-input behavior per evaluated file.

CI is read-only and downloads no datasets/models; it uploads only allowlisted synthetic
aggregate reports with7day retention. No corpus/transcript/credential is cached or uploaded.
Initial #56 headf6bf45a passed all hosted foundation and synthetic jobs; final evidence head
requires its own CI verification. Actual native runs use already-provisioned exact-hash
Moonshine v0.1.5 macOS ARM64 CPU assets; no new model/runtime/decoder dependency installed.
Apple codec services require execution outside the restricted sandbox; this was allowed for
approved corpus conversion. No microphone, TTS playback, account credential or API token is added.

## Approved corpora and licensing

User approved MUSAN/Speech Commands downloads, then explicitly approved inspecting the existing
MDC browser account and accepting/downloading the free CV26 Australian English subset plus
CC0/dataset/MDC consumer terms on14October2026. The dataset agreement was applied through the
authenticated browser, with no API credential creation or paid purchase. Its curated splits
are speaker-disjoint; extractor checks test IDs against train/dev. This is not proof of the
opaque ASR vendor's training history. No speaker identification is attempted.

- Speech Commands0.02:2428923189bytes, SHAaf14739ee7dc311471de98f5f9d2c9191b18aedfe957f4a6ff791c709868ff58.
  Archive LICENSE identifies CC BY4.0; SHA/size match pinned official TensorFlow checksums.
- MUSAN SLR17-2015:11086114085bytes, SHA86d1061c7e15b5c9e906777685c519701df51bfde3001e1070dcc9ffac955ee1,
  LOCAL_OBSERVED. Compilation is CC BY4.0; embedded music/noise component rights differ.
  Initial12-file noise pool selects only Free Sound's declared Public Domain recordings;
  exact inventory and attribution are retained and hashed. Other components are excluded.
- Common Voice26/MDC Australian English:2238607360byte Safari-decompressed TAR, locally observed
  checksum pinned in registry.json. The original1.94GB provider gzip was automatically
  decompressed by Safari, so its compressed checksum is unavailable and is not invented.
  Source card/approval summary and terms are locally hashed; CC0 does not override no-rehost
  or no-speaker-identification conditions. No full88.43GB English27 release was downloaded.

Audio/TSVs/receipts/subsets/results remain in ignored `.local/datasets`; browser's approved
CV TAR remains in Downloads as well. No large dataset, transcript, speaker ID, model or binary
is committed/uploaded. Public summary outputs contain aggregates, provenance and slices only.

## Actual diagnostic results

All clips come from official/curator held-out test membership with seed0; WAV/PCM/source
hashes freeze inputs.150native ASR executions:30clean Speech Commands,90MUSAN-noise variants
and30Common Voice Australian English clips. No result is a full-corpus or physical pass.

| Input | Clips | WER | Command overall | Target-word accuracy |
|---|---:|---:|---:|---:|
| Speech Commands clean |30|33.33%(10/30)|90%(27/30)|66.67%(6/9)|
| +noise20dB SNR |30|36.67%|86.67%|55.56%|
| +noise10dB SNR |30|43.33%|86.67%|55.56%|
| +noise0dB SNR |30|70%|76.67%|22.22%|
| Common Voice Australian English |30|24.69%(60/243)|not applicable|not applicable|

Speech Commands CER34/133=25.56%; Common Voice CER178/1259=14.14%. The command set has21unknown
and9target clips: overall accuracy is imbalanced; clean observed-label balanced accuracy is
64.29%. Command recognition is an exact ASR-word mapping, not Eilo command controller/wake-word
acceptance. Desktop RTF includes process/model/vendor-integrity initialization per clip and
cannot establish phone latency. Requested and achieved SNR/gains are recorded per variant;
selected MUSAN noise uses a frozen12-file pool. These samples expose accuracy/noise weaknesses
but cannot accept or reject the unrun physical200-ASR-strata requirement.

## Remaining blockers and review gates

Public corpus licensing/access is resolved for these exact selected inputs. No additional
permission is currently required. Larger/different datasets or materially different terms
need their own scope/license review. Full-corpus/multi-accent coverage remains unmeasured.

Native VAD and reviewed time-aligned endpoint annotations are absent: VAD results remain
NOT_RUN. MUSAN categories are weak labels; scoring cannot treat them as reviewed frame truth.
Real-corpus regression baseline approval is pending; synthetic self-comparison cannot supply
one. Accuracy measurements are diagnostic and need subsequent tuning/representative coverage.
Physical capture, interruption, endurance, standby, screen-off and device latency remain
NOT_RUN, with original production capture/trust/voice/background/Android blockers unchanged.
No supported platform, changed requirements, persistent memory or release/deployment is approved.
