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
the final partial chunk. The phone must retry preparation on the updated binary.
