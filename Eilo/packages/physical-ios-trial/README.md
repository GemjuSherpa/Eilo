# Internal iPhone foreground trial

Separate native-only app `com.eilo.ForegroundVoiceTrial`; the shipping Eilo app, trust map and
storage gates are untouched. Models are existing approved cached assets, verified before the
unsigned build and on phone installation into an ephemeral ES256 lab pack. No download occurs.
Ephemeral keys/license evidence are lab fixtures, not production approval. Model weights and
native runtime binaries stay in ignored local build directories and are never committed.

The operator has authorized a foreground microphone/speaker trial. On 19 October 2026 the
connected iPhone reports iPhone18,2 / iOS26.6.1 build23G83, Developer Mode and developer image
services available. The operator authorized existing-account development signing/profile registration and installation.
The separate app is signed and installed; no App Store release was performed. The first physical
attempt stopped at model preparation, before any probe, capture or model reply. A reproduced
directory-URL containment mismatch was fixed with activation and symlink/traversal regressions;
physical retry remains required. Closed preparation-stage codes contain no paths or error text.

## Controls

1. Grant microphone permission explicitly. This requests OS permission only; it starts no audio.
2. Prepare models. Hash/signature verification and public-model copying run on an installer worker.
3. Play the fixed English voice probe, with Airplane Mode on and Wi-Fi/Bluetooth off. Select only
   an available nonpersonal English voice. The operator declaration is recorded at build time;
   it is not an OS radio measurement or egress audit. The app never infers a new declaration.
4. Confirm hearing the complete phrase on the phone. This is one phrase of functional evidence,
   not voice quality acceptance. SDK completion alone never grants that operator attestation.
5. Microphone check: say a short nonpersonal sentence after **Speak now**. The real capture slot,
   16/48 kHz converter, signed VAD/ASR installer and native decoding run. The transcript is shown
   on the phone only. Confidence is unavailable, so RecognitionPolicy requests clarification;
   it does not invent confidence to permit an automatic generated reply.
6. Fixed synthetic prompt: a separate controller with no capture effect submits "Name one colour."
   to the signed local CPU model and screened SDK clause queue. Its synthetic confidence is not
   evidence of ASR calibration. Model starts/completions are counted separately from microphone
   finals/clarification completions. Both speech paths use gain0.4, matching the probe.

Stop, lock, resignation, interruption or route disconnection revoke queued callbacks and stop
capture/speech. A newer run rejects older completion callbacks. No auto-resume occurs. Capture
is released before playback; no full-duplex or echo-separation evidence is claimed. Public model
preparation can be cancelled; no user audio is written to disk. Releasing Swift/SDK String references
is not a forensic erasure guarantee. The trial times out after45seconds; timeout is not a pass.

`Documents/trial-results.json` contains only phase, aggregate counters, public voice/port IDs,
OS/build and hardware RAM. No serial/UDID, audio, transcript, prompt or generated reply is exported.
`report.py` rejects extra/content fields, false acceptance, inconsistent completions and malformed
metadata before accepting an owned-app export. All physical gate acceptance remains NOT_RUN;
production remains NOT_ENABLED. Charging/USB and these few functional tests do not meet the frozen
latency, quality, interruption, endurance, battery, privacy or S08 decision protocols.

## Build without signing, installing or accessing audio

```sh
python3 packages/physical-ios-trial/build.py \
  --asr-cache "$ASR_CACHE" --vad-cache "$VAD_CACHE" --vad-model "$VAD_MODEL" \
  --llm-cache "$LLM_CACHE" --llm-model "$LLM_MODEL" --output "$NEW_OUTPUT" \
  --operator-radio-off-attestation
```

Use the final flag only after the human operator declares Airplane Mode on and Wi-Fi/Bluetooth
off. Without it, the app's audio controls are disabled. `operator.json` distinguishes declaration
from device verification and records its timestamp. Keep the declared radio state throughout.
The build generates a separate local Xcode project, rebuilds the CPU LLM from pinned source,
isolates ASR behind four exports/TWOLEVEL and embeds that runtime. It never edits the normal
Xcode project or supplies an Apple account/team/certificate. Signing/provisioning is a separate
operator-authorized Xcode step; installation/launch and actual tests remain separate evidence.

After authorization and installation, export only this app's aggregate file using devicectl
`device copy from --domain-type appDataContainer --domain-identifier com.eilo.ForegroundVoiceTrial
--source Documents/trial-results.json`. Validate with `python3 packages/physical-ios-trial/report.py
LOCAL_JSON --output NEW_AGGREGATE_JSON`. Never export other apps, model folders or phone logs.

Verification: both SDK strict typechecks include the trial UI; a portable Swift epoch probe checks
Stop/replacement revocation without OS operations. Normal/optimized Python tests check reports.
The normal mobile app is separately built/installed and launched three times before a code-task
commit; those simulator launches are not physical voice results. S10/S11 remain dependency-blocked.

## Physical preparation follow-up

The next phone attempt closed after waiting; an attached trial-only console observed signal9.
No matching crash or memory-termination report was available, so the OS termination cause is
unconfirmed. Local optimized replay of the ten pinned bundled artifacts, inside one outer
Autorelease pool, found temporary FileHandle buffers retained across repeated checksum passes.
Draining a pool per64KiB read reduced maximum resident memory from2,113,404,928 to11,370,496bytes
in one local run per version, with all verification/activation still passing. See
`tests/preparation-memory-diagnostic.json`. This is a Mac diagnostic, not an iPhone measurement
or a physical gate result. A multi-chunk regression checks repeated proofs and corruption in
the final partial chunk. The subsequent phone retry completed preparation and foreground checks; see below.

## Completed foreground checks — 19 October 2026 (Melbourne)

`tests/physical-foreground-results.json` is the validated owned-app export after the operator
completed the retry: heard probe, three microphone finals with three completed clarifications,
and two completed synthetic model turns out of three starts. The earlier incomplete model
start remains counted; no success is inferred for it. Final phase is SINGLE_TURN_SDK_COMPLETED,
with audio session deactivated. The operator reported successful tests. SDK completion does
not separately score audibility or answer correctness.

The microphone path is uncalibrated ASR → clarification; the model path uses a fixed synthetic
prompt with no microphone. This does not establish an automatic microphone → generated-answer
conversation. Radio state is an operator declaration, not OS measurement or an egress audit.
Export timestamps remain device UTC; the review date uses Melbourne time. Signed binary and
source hashes are in `tests/signed-physical-build.json`; unsigned-build-results.json remains
the earlier unsigned snapshot. S08 remains HOLD and physical acceptance NOT_RUN; screen-off,
interruption, timing, endurance, battery, privacy and Android protocols remain outstanding.

After the native installer fixes, both source-bound native evaluations were rerun from cached
approved models: the eight-case signed VAD/ASR installer and file-fed capture → local model →
SDK speech evaluator passed. Their current reports and source audits were refreshed together.
The existing host-JNI report is retained; no new Android device execution is claimed.

## Listening survey contract (VC-VOICE-06 preparation)

A separate partial listening survey uses the existing 12 frozen phrases. Operator scores are
1–5 (1 unintelligible, 5 fully clear); SDK completion only unlocks rating controls. Stop,
interruption or background invalidates pending callbacks/ratings. Retries are retained and
bounded to three attempts per phrase. No automatic rating or acoustic timestamp is inferred.
`TrialVoiceSurvey.swift` owns the bounded state; the portable probe covers stale/duplicate
completion, invalid/premature ratings, cancellation and limits. `voice_survey.py` rejects content,
out-of-order or duplicate rated phrases, unknown fields and fabricated timing/network acceptance.
Partial scores never populate the frozen physical-voice-trials acceptance report. Survey state
is a lab fixture, not production voice readiness. The scrolling UI collection integration is developed on its own task branch,
consolidated into one sprint PR.

The survey requires prepared models and the heard offline probe as session setup. Scroll to
**6. Play next listening-survey phrase**, listen once, then select a score from1–5 after SDK
completion. Repeat for12phrases; no microphone control is needed. Stop/background revokes the
pending score, retaining the attempt. The exact voice ID remains fixed within one app session.
Only fixture IDs, SDK attempt states and operator scores are exported in a separate owned file
`Documents/voice-survey-results.json`; no audio/text, acoustic onset or traffic measurement.
State is session-local: export the latest survey before restarting the app or starting another
session. The display does not reveal the fixed phrase text before a score. Ratings are unblinded
single-operator listening evidence, not an independent quality study or production readiness.

## Operator results — 19 October 2026 (Melbourne)

The validated `tests/listening-survey-operator-results.json` records all12 frozen phrases,
12SDK-completed attempts and12operator scores of5/5, with no retries. The exact installed voice
is com.apple.voice.super-compact.en-AU.Karen on iOS26.6.1/build23G83. This is one operator's
listening assessment in a single foreground session. No independent timing, traffic measurement,
Android trial or general voice quality acceptance is inferred. The original one-score export
was partial; completion is established by this later full export. Raw audio/text was not collected.
The signed build snapshot retains its historical awaiting-operator status; this separate result
supplies the completed ratings. S08 HOLD and production readiness gates are unchanged.

## Six-file iPhone ASR diagnostic (VC-TURN-10 supporting evidence)

The separate lab app can run the six existing checksum-frozen synthetic ASR fixtures directly
through the signed native ASR lease on its installer worker. Control7 starts it explicitly;
`--run-file-asr-diagnostic` is an opt-in development launch argument that prepares the pack
and runs the same file-only path. Neither path opens microphone or speaker. Stop/background
revokes the worker capability and prevents stale results; the worker also checks a180second
whole-run deadline. Native calls are cooperative and cannot be forcibly preempted mid-call.

Build staging verifies the original WAV format/hash and deterministic float PCM hashes from
`tests/asr-pcm-pins.json`. Scoring uses the existing frozen lowercase ASCII normalization and
substitution/deletion/insertion tie order. Only case IDs, input hashes, sample/edit counts and
local file-ASR runtime are exported in `Documents/file-asr-results.json`. These durations include
stream creation/inference; they are not acoustic first-response latency. No transcript/reference
text is exported. Bundled fixtures are the existing synthetic files, not new microphone recordings.

`file_asr_report.py` rejects changed inputs, missing cases, inconsistent counts, nonfinite timing
and unsupported content/acceptance claims. Incomplete/cancelled runs contain no success rows.
This small single-voice diagnostic is not the physical200-utterance/accent/noise matrix; microphone
recognition quality, confidence calibration and the full S08 gate remain NOT_RUN. SDK compilation,
synthetic scoring tests and actual device execution are recorded as separate evidence.

### Device result — 19 October 2026 (Melbourne)

The owned iPhone export in `tests/file-asr-device-results.json` completed all six files:
6word errors/40reference words (15%WER), matching the existing small synthetic baseline.
Measured file-ASR runtime including stream creation was301–535ms per case. This is a device
file-inference diagnostic, not microphone accuracy or acoustic response latency; the limited
six-case result cannot accept the200utterance matrix or the broader quality targets. No raw
transcripts/references/audio were exported. Initial development installation stalled; stopping
only that client and retrying with a180second timeout installed successfully. The explicit
file-only launch then completed; signed build/source provenance is in `tests/file-asr-build.json`.

CI also validates the committed twelve-score operator export and six-case device ASR export in
normal and optimized Python, so their shape, frozen inputs and scope remain checked after review.

## CPU model diagnostic

Control8, or explicit `--run-cpu-model-diagnostic` at a fresh launch, runs the six
frozen `llm-runtime/tests/model-comparison-fixtures.json` prompts without opening
microphone or speaker. One diagnostic is allowed per app process; always use a
fresh process for each candidate. The builder accepts `--comparison-model`
`Qwen3-1.7B-Q4_K_M` (default) or `Qwen3-0.6B-Q4_K_M`, with exact reviewed file
size/SHA-256 from `tests/model-comparison-pins.json`. Arbitrary model pins are not
accepted. Each prompt opens a fresh native model handle; OS caches are uncontrolled.
Both use the existing CPU runtime, two threads, context4096, greedy sampling,
output limit256, native Qwen rules/template and thinking disabled.

The aggregate `Documents/cpu-model-results.json` records fixed fixture IDs and
counts only. Generated text is discarded. `begin_wall_ms` includes native prompt
tokenization, context creation and prefill; `first_native_piece_from_begin_ms`
ends after `eilo_llm_next` releases its first nonempty piece, including that call's
native decode. These are wall-clock diagnostic boundaries, not pure prefill,
acoustic latency or externally verified token timing. Opening/loading is measured
separately and includes descriptor verification. Stop/background revokes results
and requests native cancellation; the 600-second deadline is cooperative. The foreground diagnostic temporarily
disables the idle timer and restores its previous value on completion, failure,
Stop, or backgrounding; this does not authorize background or screen-off runs.

Memory is the public Mach TASK_VM_INFO ledger's native process-lifetime footprint
peak, read only when the returned struct includes the field. It includes model
preparation and all earlier activity in that process, and is never reset per row.
Do not infer a per-prompt or model-only allocation peak. Automatic fresh-process
launches provide the comparison path; manually running earlier trial controls
can contaminate the lifetime high-water mark. Unsupported OS memory metrics fail
the diagnostic instead of substituting RSS or a sampled maximum.

Validate exports using `python3 packages/physical-ios-trial/model_diagnostic_report.py PATH`.
Quality, independent network observation, Android and full VC-LLM-06 physical
acceptance remain NOT_RUN even after this limited diagnostic completes.


The audited C++ wrapper has an exact 1.7B file-size guard. `model_wrapper.py`
generates a lab-only source copy with precisely the selected candidate's pinned
size; the base file remains unchanged. The full base source SHA-256 and exact
candidate size/hash must match the two reviewed pins before specialization.
Only that numeric constant changes: descriptor checks, Qwen3/Q4_K_M validation,
CPU settings, cancellation and decoding are identical. The Swift lease still
verifies the exact candidate SHA-256 before passing its descriptor. Build evidence
records both base and compiled wrapper hashes. Tests reject altered source and
unreviewed candidates and prove the default 1.7B copy is byte-identical.


Both physical candidates completed all six fixed prompts on the same connected
iPhone17 Pro Max / iOS26.6.1 in separate fresh processes. The aggregate pair is
`tests/cpu-model-device-results.json`; signed source/wrapper/build provenance and
the cancelled/failed attempts are in `tests/cpu-model-builds.json`.

| Candidate | Median begin wall ms | First native piece from begin ms (range) | OS lifetime peak MiB |
|---|---:|---:|---:|
| 1.7B | 18350 | 16370–19099 | 527.9 |
| 0.6B | 5867 | 5610–6053 | 521.3 |

This is one six-prompt run per candidate in fixed order, with uncontrolled OS
caches and no independent traffic, acoustic, thermal, energy, endurance or human
quality measurement. Footprint values are not model file sizes or a complete
memory audit. The first 1.7B attempt was cancelled after foreground revocation;
the fixed retry completed. The first 0.6B attempt failed at the original exact
size guard; the reviewed lab specialization then completed. Neither attempt was
counted as success. The ordinary shipping wrapper remains byte-identical.
CI validates the actual pair in normal and optimized Python. Full VC-LLM-06 and
S08 acceptance remain NOT_RUN/HOLD pending the missing evidence.


## Human model-answer quality collection

Control9 generates one of the six frozen generic prompts with the current exact
model pin. It shows the prompt, frozen rubric and bounded answer as plain UIKit
text after generation. The operator rates correctness/clarity from1 (incorrect or
unusable) to5 (correct and clear), then the answer clears. Generation cannot
supply a rating. There are at most three attempts per fixture; Stop, background
or interruption clears the pending answer and revokes its score controls.
The idle timer is temporarily disabled during foreground generation and restored
on every exit. Other trial controls are disabled while a quality rating is pending.

The complete answer must be valid UTF8, at most16KiB, contain no prohibited
control characters or reasoning/role/tool/tag markup. Mathematical comparisons
remain plain text. This lab display guard is separate from the unchanged spoken
output guard and never authorizes speech. Worker byte buffers are cleared; no
claim of complete private-memory erasure follows from removing UI text.

Only IDs, attempt status, genuine human scores, candidate/corpus pins and OS/session
metadata save to `Documents/model-quality-results.json`. Answers, prompts, rubrics,
audio and timings are not exported. Ratings are session-local; leave the app open
for export after all six. Starting a new review session can replace that candidate's
previous file. Export before replacing the app with the other candidate. Saving
errors are displayed and prior in-memory scores retained.

Validate with `model_quality_report.py`; `--pair` requires six scored fixtures for
each exact candidate in distinct sessions. Human results have NOT_RUN status until
actually collected; the contract/controls do not create scores. Quality collection
alone does not complete the full comparison protocol, independent traffic,
Android or S08 feasibility acceptance. One consolidated PR follows the completed
collection sprint and actual operator evidence.


Both candidates completed six genuine operator rubric ratings on iOS26.6.1.
No generation failed or was cancelled in these quality sessions. The individual
exports and validated pair are in `tests/model-quality-*-operator-results.json`
and `tests/model-quality-operator-results.json`; build/source provenance is in
`tests/model-quality-builds.json`.

| Frozen fixture | 0.6B rating | 1.7B rating |
|---|---:|---:|
| compare-01 | 4 | 1 |
| compare-02 | 5 | 5 |
| compare-03 | 4 | 5 |
| compare-04 | 5 | 1 |
| compare-05 | 5 | 5 |
| compare-06 | 5 | 5 |
| Mean of six | 4.67 | 3.67 |

These are one operator's unblinded ratings of six fixed replies per candidate,
with 0.6B reviewed first. They do not establish general model preference or
complete the repeated cold/warm, alternating-order, thermal, traffic or Android
protocol. The two scores of1 for 1.7B are preserved as entered. Generated answers
were only visible during review and are absent from every exported report.
CI validates the actual completed pair in normal and optimized Python.

### Opt-in native phase telemetry

`phase_wrapper.py` derives an additional lab-only adapter from the same full-hash-checked base and two exact model pins. It adds numeric worker-thread timing without changing the ordinary adapter, one-generation lifecycle, cancellation checks or cleanup. It is not used by the default build. `include/eilo_trial_metrics.h` documents the seven native monotonic boundaries. Prefill covers the prompt decode loop, excluding tokenization and context/sampler/batch allocation; first-token timing ends after sampling, before byte conversion and the next-token decode required by the ordinary piece API. It is distinct from first returned piece latency. Timings include instrumentation overhead. The native load call uses mmap; it does not force every weight page resident, so later page faults can contribute to prefill/generation.

An aggregate snapshot is readable only on the same worker after successful generation completion (including after handle destruction), before the next load. Failed/cancelled runs cannot publish it. There is no prompt, answer or handle in this interface. This does not establish resident-model warm reuse, filesystem cold caches, physical performance or production acceptance.

With an existing approved runtime cache, run `python3 check_phase_contract.py --llm-cache PATH`: it verifies the full source tree against its pinned archive, reruns the 31 original scripted lifecycle scenarios against the instrumented adapter under ASan/UBSan, then tests completion-only publication, cleanup preservation, revocation on new load/failure/cancellation, wrong-capacity rejection, timing ordering and thread isolation. `tests/phase_smoke.cc` is an explicit local fixed-input real-runtime probe; verify the exact model SHA before running it. Desktop results never populate phone result rows.

Build with `--phase-measurements` to link the instrumented copy and enable control 10, or launch that explicit build with `--run-native-phase-diagnostic`. Default builds retain the prior adapter and hide the control. The foreground runner uses the existing verified descriptor lease, greedy CPU/two threads/context4096/output<=256, three sequential rounds of the same six frozen prompts, one newly loaded handle per sample, no audio, a cooperative 30-minute deadline and cancellation on Stop/background. It temporarily enables battery monitoring and disables the idle timer, restoring both on every completion/cancellation path. Completed numeric rows are atomically saved after each sample to `Documents/native-phase-results.json`; failed/cancelled sessions retain completed rows without inventing missing samples. Export before replacing/restarting the app.

`python3 phase_report.py REPORT` validates the closed schema and prints per-fixture phase medians/counts; `--pair` requires 18 samples for each of the two distinct pinned candidates on the same OS/RAM with distinct process sessions. The validator rejects content fields, wrong pins/order/types, inconsistent timing, stale memory peaks and impossible battery/thermal states. Battery level may explicitly be unknown; USB-connected battery observations are not energy consumption measurements. Memory remains the OS process-lifetime peak including preparation. No raw text is saved. These are reload repetitions with uncontrolled OS caches, not true cold-cache/resident-model warm, alternating-candidate, network-isolation, background or Android acceptance. No feasibility gate is promoted.

### Explicit lab resident-weight scopes

`resident_wrapper.py` derives a separate opt-in adapter from the full-hash-pinned phase variant. An explicit same-worker scope selects only index 0 (the exact pinned 1.7B) or 1 (the exact pinned 0.6B), retains at most one generic model and permits at most three generation loads. Every descriptor is still verified by the Swift signed-store lease; warm reuse additionally requires the same regular-file device/inode and CPU thread setting. Each generation uses a fresh ordinary handle and clears its KV cache, context, sampler and batch at completion. Only generic weights survive successful DONE. Scope close, native failure/cancellation or abandonment frees the cached model. The default audited adapter is unchanged. No complete vendor-memory erasure claim is made.

The worker must end a scope after destroying its handle; Stop/background must first cancel and join that worker. `include/eilo_trial_residency.h` exposes aggregate allocation counters only after successful handle destruction, distinguishing one actual vendor model load from three generations. It accepts no paths, prompt content or arbitrary model size. `check_resident_contract.py --llm-cache PATH` checks the verified cached runtime source, all 31 original ABI scenarios and new ASan/UBSan scope/reuse/revocation tests. `tests/resident_smoke.cc` is an explicitly invoked fixed-input local probe; hash the exact approved model before running. Desktop evidence does not fill phone rows.

Build with `--phase-measurements --resident-comparison --comparison-model Qwen3-1.7B-Q4_K_M --llm-model PINNED_17B --secondary-llm-model PINNED_06B` to stage both exact approved models in the same synthetic signed lab pack. Default builds remain single-model. The explicit resident build hides the audio and unrelated diagnostic controls; use control 11 or `--run-resident-model-comparison`. Its 12 groups cover the six frozen prompts, reversing candidate order for every fixture. Each group runs one model-unloaded generation then two generations reusing only generic weights. Each generation still verifies the signed-store descriptor, allocates fresh context/KV/sampler and discards output. Cold here means the model is not resident in the lab scope; processes and OS filesystem caches are reused and disclosed, not flushed. Resident means the same model object/mappings remain owned by the lab scope; pages are not locked in RAM and can still fault or be reclaimed by the OS.

The foreground worker waits up to five minutes before every sample until the OS reports nominal or fair, and does not start a sample at serious/critical thermal state. Total deadline is one hour, cooperatively cancelled on Stop/background; no background inference or keepalive is added. Idle/battery-monitoring settings are restored and completed aggregate rows are saved after each sample. Thermal limits/failures retain partial evidence rather than inventing completion. `resident_report.py REPORT` validates exact pins, the 36-sample alternating schedule, one actual vendor load/three fresh generations per group, zero warm vendor-load time, thermal policy, per-sample cooldowns, clock/memory consistency and closed content-free fields; it reports per-fixture cold/warm counts and medians. Results stay supporting evidence: independent traffic, new-output quality ratings, Android, energy/endurance and permitted background remain separate acceptance requirements.

The initial schema-1 nominal-only trial stopped at `THERMAL_LIMIT` after six genuine samples because the phone stayed fair through the five-minute nominal wait. Its aggregate and original signed build are retained in `tests/resident-initial-thermal-limit-results.json` and `resident-initial-build.json`, validated by the frozen `resident_report_v1.py`. Schema 2 records the revised below-serious policy and cooldown before every sample, including warm samples while the same generic model remains owned. The original protocol requires thermal observations, not nominal-only execution. This adjustment does not promote any physical acceptance gate.

## S04 bounded physical lifecycle observations

Control12 provides six ordered lab cases: playback and capture, each stopped by the explicit
Stop button, scene resignation to Home, or an operator-requested lock/unlock. Each case has at
most three attempts; failed attempts remain in the export. This target has no background audio
mode. The capture cases use the existing native owner and bounded erased ring only: no wake,
recognizer, model generation or file recorder is attached. Playback uses a fixed nonpersonal
phrase at gain0.4. An unattended case times out at35seconds and cannot pass.

After fresh operator radios-off confirmation, install the separate lab build using existing
approved caches. The pinned0.6B candidate can reduce installation staging; these cases do not
run the LLM. Local signing success is distinct from iOS trust and successful launch. Preserve
owned aggregates before updating. Do not remove the lab app or its data without authorization.

1. Grant microphone permission using the no-capture control, prepare models, play the offline
   probe and confirm hearing it. Keep the phone unlocked and use the built-in route.
2. Tap control12. Wait for the label to say audio is active, then perform the requested action.
   For Stop, tap **Stop and clear**. For Home or lock, wait five seconds before returning to the
   app. Remain quiet during capture; no speech is needed.
3. Wait for the two-second foreground verification before starting another case. Backgrounding
   invalidates the earlier heard-probe state: replay/confirm the offline probe when needed.
4. After six observations, keep the app open. Export only `Documents/lifecycle-results.json`
   from `com.eilo.ForegroundVoiceTrial`, then validate with `lifecycle_report.py`.

The observations require actual SDK/controller active state before the action; controller Stop,
no pending capture, cleared volatile UI/request ownership, revoked epoch, SDK no-speech state
and successful audio-session deactivation; and a later foreground snapshot still stopped. The
Swift state probe covers early Stop, wrong events, release failure, return requirements,
resumption, stale/duplicate observations and the retry cap. Python checks reject extra content,
missing/reordered cases, false gate promotion and unsupported lock/network claims.

`SCENE_RESIGNED` does not identify its cause as a hardware lock. The case ID records the action
requested of the operator, not independent OS lock proof. The aggregate contains no audio,
transcript, token/handle, serial, path or external endpoint. It is controller/SDK-boundary evidence,
not a forensic memory/storage audit or independent acoustic stop measurement. The two-second
snapshot is not a300ms interruption result. These cases do not enable or accept screen-off
capture, sustained workload, voice barge-in or automatic microphone→model replies. Physical
S08 gates and network observation remain NOT_RUN; release HOLD and memory disabled are unchanged.

### Dedicated lifecycle UI and restart handling

Use `--lifecycle-only` for the S04 lab build. It shows setup, **Lifecycle** and Stop controls;
unrelated recognizer/model/survey controls and automatic inference launch arguments are hidden
or ignored in that build. Normal lab builds retain their other diagnostic controls.

The Lifecycle label reports its disabled reason (prepare models or replay/confirm the probe)
and the previous case's actual OBSERVED/FAILED outcome. Going Home means returning to the Home
Screen without swiping away the app card. Swiping the card ends the process and requires fresh
setup. Reopening never resumes microphone or playback automatically.

Before a new process writes `lifecycle-results.json`, it preserves the prior metadata-only
report byte-for-byte under the owned `Documents/lifecycle-archive` directory, named by its content
SHA256. Repeated preservation is idempotent. A prior IN_PROGRESS case stays incomplete; it is
never converted into a completed return-to-app observation. New processes begin a fresh sequence.
Reports from separate source builds/processes must retain their separate provenance.

Preservation accepts only the existing bounded, closed aggregate format and public OS metadata,
rejects unexpected content and symlink files/directories, and never overwrites a different archive.
If preservation fails, the current primary report is left intact and lifecycle controls stay
blocked for review. Archive regressions exercise byte equality, repeated startup, same-process
exclusion, interrupted-case retention, extra-content rejection and symlink containment. No raw
speech, prompt, generated reply or model asset is persisted by this helper.
