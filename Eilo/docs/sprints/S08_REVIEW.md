# S08 — physical voice feasibility evidence preparation

Awaiting Gemju Sherpa review. **Available measurement/reporting prerequisites are prepared; S08 physical acceptance and feasibility decision are incomplete.** Neither platform is declared supported. Do not advance persistent memory through this gate.

PR50 is reviewed/merged at96e3553d7a85e3a281084479f318a02f18716cb5; all three final CI jobs PASS. It provided VC-VERIFY-02 meaningful-audio tooling. This sprint covers the remaining five task preparations, each on a separate branch, built/tested/committed/pushed and merged to `sprint/s08-feasibility-evidence`, then one PR for review. Main merge remains for Gemju Sherpa.

| Task | Delivered | Physical acceptance |
| --- | --- | --- |
| VC-VERIFY-02 | Reviewed cold/warm acoustic evidence tool from PR50 | NOT_RUN; native capture pipeline/corpus/independent acoustic evidence missing |
| VC-VERIFY-03 | Frozen100 interruptions/20 noise controls, acoustic p95/failed-attempt accounting | NOT_RUN; native capture/separation and acoustic corpus missing |
| VC-GATE-01 | Full60min resource/acoustic/final15 scoring and incomplete-run handling | NOT_RUN; native pipeline and full physical trace missing |
| VC-GATE-02 | Same60min accounting plus reviewed consent/permitted generic locked policy/screen evidence | NOT_RUN; current locked/background capture denied, prior physical policy gates open |
| VC-GATE-03 | Full8h/481 observations, directed wakes/false activations/availability/battery accounting | NOT_RUN; locked standby denied, ambient corpus/pipeline unavailable |
| VC-GATE-04 | Checksum-linked both-platform pending decision report and source-policy blockers | Pending Gemju Sherpa decision; recommendation HOLD_PENDING_PHYSICAL_EVIDENCE |

## Checks

PASS:47 combined synthetic evidence regressions in ordinary and optimized Python; strict Python compile checks; each default report validates without generating fake metrics. Existing voice/model physical records remain NOT_RUN; their current reason now reflects connected iPhone rather than obsolete offline state. No historical failed evaluation is removed. Six decision-report regressions reject inferred support/memory approval, missing dependencies and stale artifact/source hashes.

Normal same-iPhone18 Pro/iOS27 app build/install and three fresh ten-second startup checks precede each of the five task commits (15 launches total). Per-task `S08_VERIFY03_VALIDATION.json` and `S08_GATE01/02/03/04_VALIDATION.json` record actual results. The app and native inference/capture sources are unchanged; startup is not physical speech. Existing workspace lint/typecheck and9mobile/33contract tests run for the final sprint; legacy React `act` warnings remain in the passing App tests. Hosted checks are recorded on the final PR and must not be inferred from local checks. Staged/full new-history secret scanning precedes publication.

Reproduce all tools/tests using `packages/voice-latency/README.md`. CI runs the47 synthetic checks and all six default reports without microphone/models/downloads. Additional dependency installs/services/deployment/paid tools are not used.

## Actual prerequisites and decision

Physical iPhone17 Pro Max/iPhone18,2 on iOS26.6.1/build23G83 is paired/connected. RAM, battery health and approved offline voice/corpus are not yet established. USB connection is not a valid uncharged battery workload. No Android phone. No physical acoustic latency, interruption,60min/endurance or8h standby results are fabricated or marked passed.

Source inspection, pinned in `S08_FEASIBILITY_DECISION.json`, establishes current implementation gaps:

- iOS normal controller still defaults to MissingModelReadiness; app PackStore has an empty trust map and no native wake/VAD/ASR/LLM/voice pipeline attached. Android's PackStore trust map is also empty.
- iOS scene resignation and protected-data loss stop capture; eligibility does not enable production background execution. Android capture requires unlocked state. Source policy is an implementation blocker, not a measured physical failure or an OS impossibility determination.
- VC-TURN-09 physical100-wake/8h ambient trials and VC-TURN-10 physical200-ASR-strata trials are unrun. Retained six-fixture simulator ASR WER15% is above the10% target for that limited synthetic set; it cannot be relabelled a physical pass or physical failure.
- VC-VOICE-06 acoustic/installed-offline-voice/traffic/intelligibility and VC-LLM-06 physical1.7B-vs0.6B comparison remain unrun; the0.6B artifact/exact comparison adapter is unprepared.

The pending matrix retains all nine VC-GATE-04 dependencies for both platforms, references actual tracked artifacts with SHA-256 and keeps supported configurations empty/persistent memory disallowed. The report checker validates the pending report, not platform capability, declarations' truth, quality/safety/privacy, App Review or release compliance. No consent/trust/confidence/offline/background gate is weakened to manufacture measurements.

The concrete route to physical completion is: attach the reviewed real native pipeline and exact trusted/licensed pack/offline voice; freeze/review acoustic and8h corpus and exact device/route/resource conditions; prove permitted generic lock/background behavior in VC-AUDIO-09/10; collect and review prior wake/ASR/voice/model trials; perform actual100 timing/interruption,60min foreground/screen-off and8h standby workloads; then obtain Gemju Sherpa's explicit per-platform feasible-scope decision. Requirement/scope changes need separate review. No persistent memory work is started by this PR.

## Source control

Separate task branches: `task/s08-vc-verify-03-interruption-evidence`, `task/s08-vc-gate-01-foreground-evidence`, `task/s08-vc-gate-02-screen-off-evidence`, `task/s08-vc-gate-03-standby-evidence`, `task/s08-vc-gate-04-feasibility-report`. Exact commits/sprint merges are available in PR history and ignored stable tracker. No force-push/history rewrite/automatic main merge. Personal project signing/formatting, plist ordering and S02 review changes remain exact and excluded; ignored context files stay local. Preserve175stable backlog IDs/order/dependencies.

Review the protocol/schemas/scoring and pending recommendation. Approval of preparation is distinct from passing physical targets or accepting changed requirements. S08 stays partial until the actual prerequisites/experiments and decision are complete.
