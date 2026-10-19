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
