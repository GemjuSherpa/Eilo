# S08 continuation after PR70 — dependency-ready work complete

PR70 is reviewed/merged at `4459d123cd655b189798e82f7f6f25266d6f0521`; all eight hosted
checks passed. The current authorization covers every dependency-ready S08 subtask, separate
task branches merged into `sprint/s08-completion`, followed by one review PR. Main is unchanged.

**S08 physical acceptance remains incomplete. All six acceptance tasks are dependency-blocked;
no remaining physical task can proceed within S08 alone.** The earlier evidence-tool preparation
was implemented in PR50/51. This continuation refreshes its dependency/evidence records against
merged native work, without treating preparation approval as physical acceptance.

| Task | Ready work delivered | Remaining dependency |
| --- | --- | --- |
| VC-VERIFY-02 | Cold/warm acoustic scoring and pinned pending evidence | VC-VERIFY-01 exact reviewed matrix; VC-JOIN-01 integrated physical spoken turn |
| VC-VERIFY-03 | Interruption/noise controls and pinned pending evidence | VC-VERIFY-01 matrix; VC-JOIN-03 physical interruption/separation |
| VC-GATE-01 | 60-minute foreground scoring and incomplete-run accounting | VC-VERIFY-01 matrix; VC-JOIN-02 integrated follow-up session |
| VC-GATE-02 | Screen-off protocol, conservative scoring and policy evidence | VC-VERIFY-01/VC-JOIN-02 plus VC-AUDIO-09/10 physical locked-audio acceptance |
| VC-GATE-03 | 8-hour schedule, wake/false-trigger/battery accounting | VC-VERIFY-01, VC-TURN-02 physical wake and VC-AUDIO-09/10 |
| VC-GATE-04 | Both-platform, nine-dependency pending decision report | All five S08 trials plus VC-TURN-09/10, VC-LLM-06, VC-VOICE-06; explicit human decision |

`S08_DEPENDENCY_AUDIT.json` records exact baseline IDs/dependencies, current actions and SHA-256
links. No stable task IDs or dependency ordering changed. A merged implementation does not
satisfy its still-unrun physical acceptance. The audit does not modify the personal tracker.

## What changed since the initial S08 preparation

Selected Speech Commands/MUSAN/Common Voice inputs and offline public-corpus evaluation tools
are available under their reviewed permissions. Native VAD/ASR workers, bounded transport,
VAD→ASR handoff, 16/48 kHz conversion, signed selections/leases and the capture-ticket installer
are implemented. See the linked current PR70 review/evidence in the audit. Their scripted and
simulator/JVM evidence does not supply a phone microphone workload or full acoustic acceptance.
The public clips are not automatically the approved S08 dialogue/interruption/8-hour workload.

Normal production trust/runtime/voice-caller integration remains gated. The app still denies
the required lock/background workload; VC-AUDIO-09/10 must establish permitted physical behavior.
Prior physical wake/ASR/voice/model-comparison acceptance is open. Current hardware availability
was not rechecked because these software/workload dependencies already block collection;
the historical 14 October iPhone connection is not a claim of current readiness.

## Validation and branch record

Two independently committed task branches consolidate into this S08 sprint:
`task/s08-dependency-audit` and `task/s08-review-validation`. Changes are documentation and pending
evidence records only. No app source, inference runtime, permission, model, scoring threshold
or CI workflow changed; app rebuild/launch checks are not needed for this docs-only continuation.

PASS: 47 existing evidence tests in ordinary and optimized Python; all six default CLI reports;
exact task/dependency coverage against the 175-task baseline and sprint plan; every audit and
pending-decision artifact/source hash; prior sample/measurement fields preserved; unchanged
personal diff and staged/full-new-history secret scanning. No physical trial was run, new dataset
was downloaded, dependency installed or microphone activated. S08 issue remains open.

Production remains NOT_ENABLED; physical targets remain NOT_RUN; supported configurations stay
empty; recommendation remains HOLD_PENDING_PHYSICAL_EVIDENCE and persistent memory remains denied.
Reviewing this continuation cannot approve a supported configuration or advance persistent memory.
Complete the named earlier-sprint dependencies before returning to physical S08 collection.

---

## Historical preparation record (14 October 2026)

The following records the original PR51 checkpoint and its then-current environment; current
status and implementation progress are described above.

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
