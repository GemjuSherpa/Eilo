# Meaningful-audio latency evidence — VC-VERIFY-02

This is an offline evidence tool, not a microphone/inference app or a physical-test pass. It derives latency from reviewed acoustic frame positions on one independently recorded waveform. SDK callbacks, model-only timings, recorded-PCM injection, scripted endpoints and simulator execution do not establish N01.

`tests/turn-plan.json` freezes 100 attempts per device/route: 20 cold and 80 warm, cycling ten nonpersonal English questions. All trials use these fixed questions; no real conversation recordings. The question schedule is frozen, but the actual acoustic input corpus is **not yet prepared or approved**. VC-VERIFY-01 device/corpus review remains partial.

## Run the checks

From the repository root, using the existing Python 3 runtime (no packages/downloads):

```sh
python3 -m unittest discover -s Eilo/packages/voice-latency -p 'test_*.py'
python3 -O -m unittest discover -s Eilo/packages/voice-latency -p 'test_*.py'
python3 Eilo/packages/voice-latency/measure.py
```

The last command validates the checked-in **NOT_RUN** records. It prints null metrics and `REVIEW_REQUIRED`; this is not acceptance. Unit tests create temporary synthetic PCM files containing no speech, then remove them. Their apparent target passes test arithmetic only.

For a future annotated trial:

```sh
python3 Eilo/packages/voice-latency/measure.py /absolute/local/report.json \
  --corpus-root '/absolute/path/Eilo/.local/voice-latency' \
  --output /tmp/eilo-physical-latency-summary.json
```

Keep input WAVs, independent recordings and manifests in the already ignored `.local` directory. Do not commit raw recordings, device identifiers, serial numbers, personal utterances or logs. A report contains only allowlisted configuration, checksums, outcomes and acoustic frame positions. Different routes/configurations are separate records, never pooled. Android requires its own physical results or explicit `NOT_RUN` record.

## Prepare before recording

1. Review the exact device eligibility, model/runtime/voice/OS/route and frozen question/acoustic corpus with Gemju Sherpa. Use the normal native microphone → wake/VAD → ASR → LLM → policy → TTS pipeline. The current app has no verified production pipeline attachment; do not override missing-model, trust, confidence, voice or separation checks to collect target evidence.
2. Record built-in speaker/microphone first. Wired/Bluetooth routes require their own acoustic observation method and 100 attempts. No route is silently declared supported. Record the physical hardware model, exact OS build, route, runtime revision, model SHA-256 and installed voice identifier without a device serial/UDID.
3. Create the 100 synthetic input recordings matching `schedule` IDs/question indexes. Freeze the manifest and all hashes **before** collection. Reusing a question across repetitions is intentional. The reviewer verifies acoustic content against the frozen text; the tool cannot recognize whether a WAV contains that text.
4. After asset setup, enable airplane mode, turn Wi-Fi off and independently observe traffic. `NO_TRAFFIC_VERIFIED` is a supplied reviewed claim, not something this tool measures. An attached USB development connection does not itself establish zero egress.
5. Cold means a fresh process with models unloaded for each of the first 20 attempts; record cold-reset confirmation. Warm uses the remaining 80 attempts without repeating cold initialization. Use the same route/settings and report deviations as a new configuration.

## Record and annotate

Use an independent local acoustic recorder that observes both the emitted synthetic question and the phone's audible reply in a single PCM16 WAV, mono or stereo, 8–192 kHz. This provides a common sample clock. An app-side microphone buffer may omit playback or change routing and is not a substitute. Do not install a paid recorder. Freeze the acoustic arrangement and calibration before collection; headset/Bluetooth must include actual audible output. No new recording is initiated by the tool.

For every scheduled attempt, Gemju Sherpa reviews the waveform/listening annotation:

- `user_speech_end_frame`: true end of the input speech, before endpointing. Do not use VAD-end, ASR-final or inference-start as this timestamp.
- `first_meaningful_reply_frame`: first audible content that responds to the question. Exclude chimes, filler and “one moment”; no automatic amplitude-based guess. Both timestamps are integer frame indexes in the same independent recording.
- Retain `TIMEOUT`, `FAILED` and `CANCELLED` attempts, with a null reply frame. Timeout requires at least 30 seconds of observation after true speech end. Explain failures in the review, not personal logs. Do not delete/replace poor attempts; a corrective rerun is a separate report retaining the original.

The tool checks PCM layout, truncation, hashes, frame order/bounds, 100 exact assignments, cold-reset declarations and unique independent recording hashes. It does not prove the hardware/network/annotation declarations are truthful, verify audio content, calibrate the recorder or certify safety/privacy. Results require review of the actual local evidence.

## Evidence schema

`physical-turn-latency.json` uses `schema: 1`, `task: VC-VERIFY-02` and a `configurations` list. Each platform needs a measured or explicit unrun record. An unrun row has exactly `id`, `platform`, `status: NOT_RUN`, `reason`, `samples: []`. It cannot contain metrics.

An annotated row has exactly `id`, `platform`, `status: ANNOTATED`, `configuration`, `corpus`, `plan_sha256`, `samples`. `configuration` has:

```json
{
  "hardware_kind": "physical",
  "hardware_model": "exact physical model",
  "os_build": "exact build",
  "route": "exact observed route",
  "runtime_revision": "exact runtime revision",
  "model_sha256": "64 lowercase hexadecimal characters",
  "voice_id": "exact installed identifier",
  "network_observation": "NO_TRAFFIC_VERIFIED",
  "airplane_mode": true,
  "wifi_enabled": false,
  "cold_method": "fresh_process_models_unloaded",
  "pipeline": "native_microphone_wake_vad_asr_llm_policy_tts"
}
```

`corpus` references a relative local manifest `file` and its `sha256`. The manifest contains exactly `schema: 1`, `plan_sha256`, `frozen_before_collection: true`, and 100 ordered `fixtures`. Each fixture contains `id`, `question_index`, and `audio: {file, sha256}` for its frozen input WAV. Hashes are calculated from bytes, not JSON reformatting.

Each of the 100 ordered `samples` contains:

```json
{
  "id": "turn-001",
  "condition": "cold",
  "outcome": "REPLY",
  "cold_reset_verified": true,
  "recording": {"file": "recordings/turn-001.wav", "sha256": "exact SHA-256"},
  "annotation": {
    "method": "independent_same_recording_acoustic_frames",
    "reviewer": "Gemju Sherpa",
    "user_speech_end_frame": 1000,
    "first_meaningful_reply_frame": 9000,
    "filler_excluded": true,
    "timeout_observed": false
  }
}
```

These frame indexes are illustrative, not measured. Warm samples require `cold_reset_verified: false`. Non-replies use a null reply frame; only `TIMEOUT` sets `timeout_observed: true`. Absolute paths, parent traversal and symlink evidence files are rejected. Relative paths resolve solely within the explicit local corpus root; each WAV is limited to 64 MiB and 180 seconds.

## Scoring and current limits

Latency = `(meaningful_reply_frame - true_speech_end_frame) × 1000 / sample_rate`, including all endpointing/loading/ASR/prefill/generation/policy/TTS delay. Sorted nearest-rank median/p95 use `ceil(p × n)` (even-sized median is the lower middle, as frozen in S01). Cold, warm and overall are reported separately. Median ≤1500 ms and p95 ≤3000 ms are targets. Any non-reply prevents its group/configuration passing; failure counts are printed next to successful-reply distributions. A configuration passes only when both strata and overall pass. No rounding is applied before scoring.

Connected hardware was read on 14 October 2026 as iPhone 17 Pro Max (`iPhone18,2`), iOS26.6.1/build23G83. Its friendly name mentions a different model; the actual hardware details govern. RAM, battery health, exact installed offline voice, frozen acoustic corpus and native pipeline attachment remain unverified. No physical Android is available. No physical N01 timing has been collected, and no supported-device claim is added.

VC-VERIFY-03 interruption timing and S08 endurance/standby/feasibility decisions are separate work. This tool does not advance them or authorize persistent memory.

## Remaining S08 evidence tools

The following tools are measurement/reporting prerequisites. They do not start capture, generate real physical measurements, enable background capability or approve support. Both platform rows remain **NOT_RUN**. Schema checks and synthetic scores do not establish the truth of device/network/acoustic/resource declarations; review the actual independent local evidence.

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s Eilo/packages/voice-latency -p 'test_*.py'
PYTHONDONTWRITEBYTECODE=1 python3 -O -m unittest discover -s Eilo/packages/voice-latency -p 'test_*.py'
python3 Eilo/packages/voice-latency/interruption.py
python3 Eilo/packages/voice-latency/endurance.py
python3 Eilo/packages/voice-latency/screen_off.py
python3 Eilo/packages/voice-latency/standby.py
python3 Eilo/packages/voice-latency/decision.py
```

47 synthetic regressions pass in each mode. Tests create silent PCM fixtures and artificial timestamps/resource traces, not phone speech or an hour/eight-hour workload. Six tests protect the pending decision report against omitted dependencies, inferred approval and stale evidence. CI runs these without assets, microphone or new dependencies.

| Task | Frozen workload | Inputs and conservative accounting |
| --- | --- | --- |
| VC-VERIFY-03 | 100 interruptions at early/middle/late clause positions,20 noise controls | Reviewed intelligible-onset→final-old-audio frames on independent same-clock WAVs;≥1s post-onset observation; p95≤300ms. Misses/cancellations/resumption/noise false triggers prevent passing. Later stale audio remains a separate lifecycle audit. |
| VC-GATE-01 | 60min foreground,60 fixed question attempts,61 minute resource observations | True acoustic end→meaningful reply, final15 median/p95, uncharged battery≤15points/h, native peak RSS<2.5GB, pack<2GB, thermal/lifecycle observations and reviewed continuous-capture trace. Failures remain counted. |
| VC-GATE-02 | Same60min workload, screen off throughout | Additional reviewed consent/permitted generic locked policy/exact policy revision/lifecycle trace/no keepalive workaround. Foreground samples cannot stand in for screen-off. |
| VC-GATE-03 | 8h frozen nonpersonal ambient workload,100 scheduled directed wakes,481 minute observations | ≥95% recall,≤1 false activation/8h,≤2 battery points/h; activation count must reconcile every directed/false event. Capture gaps, forbidden revival, crash/shutdown fail. |
| VC-GATE-04 | Both platform matrices, all nine prerequisite tasks | Pending report links checksum-pinned artifacts and source-policy observations. No supported configuration or persistent-memory approval is inferred. Recommendation HOLD_PENDING_PHYSICAL_EVIDENCE; decision remains for Gemju Sherpa. |

Frozen plans live in `tests/interruption-plan.json`, `foreground-plan.json`, `screen-off-plan.json`, `standby-plan.json`. These freeze schedule and scoring; actual acoustic input and8h ambient corpus are still unprepared/unreviewed. The extra20 noise controls and100-wake standby schedule require protocol review, rather than silently asserting an existing measured workload. The decision is `docs/sprints/S08_FEASIBILITY_DECISION.json` and checks source hashes against files under Eilo; reviewed future physical results require a new decision report, not automatic promotion of this pending one.

All report schemas use strict allowlisted keys in their corresponding module; complete synthetic constructions are in `test_interruption.py`, `test_endurance.py`, `test_screen_off.py`, `test_standby.py`. For real future acoustic reports, use the first three tools' optional `--corpus-root` pointing at ignored `.local` independent PCM16 recordings. Standby consumes a reviewed full trace and frozen ambient checksum, without reading or recording ambient audio. Hashes/declarations are traceability, not proof of content or continuous availability.

Minute resource records include exact index, actual elapsed seconds (±5s cadence tolerance), battery percentage, charging=false, native RSS, thermal state, screen-off and capture availability. Start at elapsed0; final sample must cover the full duration. Peak RSS and intervening capture continuity need native-process/continuous traces, not only samples or JS heap. Actual turn emission times must follow the fixed cadence within5s. Reject clock drift, battery increase/charging, shifted cadence or missing samples. Report incomplete runs as INCOMPLETE with reason/observed duration and null full-run metrics; retain original failures when rerunning after a correction. Full annotated crash/capture/thermal outcomes are preserved as FAIL.

For physical battery trials, disconnect charging after installing assets; a connected USB phone is not a valid battery test. Keep route, brightness, volume, room temperature, battery health and network state fixed/reviewed and include them in the locally retained protocol/trace. Thermal states are observed metadata, not temperature or heat-safety certification. Use only synthetic questions/ambient sound; no personal audio, conversation, serial, location or raw exception logs in reports.

Current source policy stops iOS capture on scene inactivity/protected-data loss, and Android capture requires unlocked state. Empty production pack trust configuration and missing attached native wake/VAD/ASR/model/offline-voice pipeline block physical spoken turns. No capability flag is changed by these tools. Physical device availability is established separately from app capability. Android hardware remains unavailable. Review these gaps and legitimate platform behavior before any affected physical workload or persistent memory work.
