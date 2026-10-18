# Joined signed capture and reply evaluation

Base PR74 merged at `5d7ff049a7d9a0e02fa5b149a7f36d4aa53d70eb` with all eight hosted checks
successful. The user authorized subsequent completed sprint PRs to merge after successful tests.
Task branches consolidate into `sprint/joined-speech-capture-evaluation` before its one final PR.
This is voice prerequisite implementation/evidence work; it does not close S08 or S10.

## Completed subtasks

1. `task/joined-capture-ios-evaluation`: actual signed VAD/ASR capture -> native final -> signed
   local CPU generation -> screened clause queue -> SDK speech on the iPhone18 Pro simulator.
   Two generated spoken turns complete. The second uses 48 kHz conversion and bounded completed
   context without another wake. 29184 normalized samples and matching transcript hashes reach
   both speech endpoints; context grows from two to four messages. 80000 quiet samples produce
   no recognition, reply submission or model start. The temporary ten-artifact pack is removed.
2. `task/joined-capture-reply-regressions`: Swift and Android tests exercise a signed capture
   final followed by reply submission. Stop/privacy transitions in the intervening gap deny
   submission without model/speech; unknown confidence takes clarification without generation;
   duplicate finals cannot start another reply. These tests use scripted native APIs/sinks.
3. `task/joined-capture-evidence-ci`: exact aggregate fields, source pins, model/library inventory,
   full case coverage, context accounting and tampering checks in synthetic CI. Hosted checks
   perform no native inference or model download. Evidence contains no raw transcript/audio.

The runner verifies the cached publisher/runtime/model inputs and rebuilds the LLM libraries
from the pinned source with the recorded CPU-only settings. Mutable prior cached library hashes
did not match the historical build, so those libraries were not trusted/reused. Network symbols
are rejected. The ASR dynamic wrapper preserves four exports and two-level namespace isolation.
The speech-only strict Swift executable excludes the unrelated protected-key provider, whose
legacy deprecated keychain prompt currently raises a warning in the normal full-source build.
Normal app builds still compile it. No production source, trust map or activation changes here.

## Validation

Actual simulator execution covers two generated SDK-completed spoken turns and silence through
real VAD/ASR. It uses synthetic confidence and voice evidence, and file-fed audio. Focused
validation/tampering tests run in normal/optimized Python. Normal suites pass 306 Swift and 362
Android tests, zero failures/errors/skips; Android lint, release Kotlin and debug/release assembly
pass offline. Each code-task commit has a normal same-simulator build/install and three fresh
ten-second launches (nine total). Workspace lint/typecheck, 9 mobile/33 contract tests, existing
signed installer evidence and 47 feasibility tests remain green. Secret scans precede publication.
The original personal Xcode/plist/S02 diff remains byte-identical.

An initial new Swift test used method syntax for the isEmpty property; corrected before commit.
An initial strict evaluator compile included the unrelated protected-key provider; restricting
this speech-only executable to its actual source scope resolves that compile. An intermediate
native evaluation passed while an already-loaded older Python schema rejected its newly added
model-start counter. Its aggregate was validated with the finished schema; a fresh final complete
runner execution then verifies the finished workflow before publication. No acceptance failure
was suppressed or represented as a successful native run.

## Remaining work

Physical foreground microphone/speaker trial permission is pending. The paired physical iPhone
is available; Android physical execution and a calibrated device matrix are still absent.
Wake-to-question alignment, real full-duplex separation, route quality, first-audible/latency,
energy/endurance, screen-off behavior, egress and actual OS-authentication evidence remain open.
No physical gate is marked passed. SDK completion is not proof of hearing or acoustic quality.
Ephemeral lab keys/evidence are not production trust or licensing approvals.

S08 remains HOLD_PENDING_PHYSICAL_EVIDENCE; persistent memory remains denied. VC-STORE-01 and
all S10 tasks remain dependency-blocked, and S11 depends on that store and the unapproved sealing
composition. Continue with the selected physical prerequisite matrix/foreground voice trial once
its access scope is approved; do not manufacture physical evidence or start dependent storage.
