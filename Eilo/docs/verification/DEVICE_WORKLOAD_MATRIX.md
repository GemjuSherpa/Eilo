# VC-VERIFY-01 — device and workload protocol v1

Status: protocol ready for review, physical-device matrix provisional. No performance measurements performed. Freeze exact fixture files, hashes, device model/RAM, battery health, OS/build, model/runtime revisions and route configuration before collecting results. Do not reuse simulator measurements as phone evidence.

## Available environments

| Environment | OS | Purpose | Evidence status |
|---|---|---|---|
| Gemju Sherpa’s iPhone 17 Pro Max (iPhone18,2), RAM unverified | iOS 26.6.1/build23G83 | Future physical iOS lifecycle/performance trials | Connected 14 October 2026; RAM/voice/corpus/pipeline eligibility pending; physical latency not run |
| Physical Android | Not available | Android thermal/battery/audio/background gates | Unavailable; affected release scope blocked until obtained |
| iPhone 18 Pro simulator on M5 Mac | iOS 27.0 | Shell build/launch and development only | S01 checks; no phone performance claim |
| Eilo_API35 ARM64 emulator | Android 15/API35 | Shell build/launch and native fixtures | S01 checks; no phone performance claim |

Provisional support candidates from baseline: Android15+/iOS18+, 8GB phones. The connected iPhone has not been asserted to meet the unverified RAM/voice/workload assumptions. A new support matrix requires review.

## Frozen workload definitions (synthetic fixtures only)

| Gate | Samples and procedure | Scoring |
|---|---|---|
| N01 full-turn latency | 100 recorded synthetic English utterances/device/route; 20 cold + 80 warm, annotate true speech end; no model-execution-only timing | Speech end to first meaningful reply audio, endpointing included; filler excluded. Sorted nearest-rank median/p95, cold/warm separate; target median≤1.5s/p95≤3s |
| N02 interruption | 100 synthetic intelligible interruption onsets while speaking/device/route, varied clause positions | Onset to final audible output; p95≤300ms, stale resumption is failure |
| N03 wake | 100 directed wake samples and one frozen 8h ambient synthetic/nonpersonal set/device; phrase/checkpoint pending selection | ≥95% wake recall, ≤1 false activation/8h; report missed and false activations |
| N04 ASR | 200 reference-transcribed synthetic utterances: 50 general, 50 accents, 50 names/numbers, 50 noise/device/route; freeze audio and reference hash | WER=(substitutions+deletions+insertions)/reference words≤10%; strata separately, no punctuation/case penalty; freeze normalization before run |
| N05 conversation | 100 synthetic multi-turn scripts, 5 turns each; freeze wording and two human scorers before evaluation | Each conversation passes only with coherent, relevant, supportive responses; uncertain input handled honestly; ≥90 acceptable. Safety/privacy violation separately blocks release regardless of aggregate score; disagreements adjudicated and logged without real user content |
| N06 active endurance | Two 60min trials/device (foreground, consented screen-off), fixed turn cadence 1/min; repeat failed trials only after documented correction | No crash/thermal shutdown; final15min latency still meets N01; interrupted/unsupported OS execution reported as failure/blocker |
| N07 standby | One 8h screen-off trial/device with frozen ambient set, background consent enabled; force-quit/reboot are separate negative cases | Availability, false activation, truthful stopped state; no revival promise |
| N08 resources | N06/N07 workloads, battery start/end and 1min samples, peak native process RSS; no charging; fixed brightness/network/route/room-temperature range | Standby≤2 percentage points/h; active≤15 points/h; RSS<2.5GB; generic pack<2GB. Battery measurements on physical phones only |

Routes: built-in speaker/microphone, wired headset where supported, Bluetooth HFP; record actual hardware/model and routing changes. Repeat N01/N02/N04 per supported route. Test lock/unlock, app background/foreground, microphone denial/revocation, call interruption, route disconnect, private/history modes and airplane mode after asset installation. No capture tests occur before their separately approved task.

Dataset acquisition/generation and exact hashes are pending ASR/wake/model task selection; this is a premeasurement protocol, not a frozen audio corpus. No real conversations or personal recordings may be collected for debugging. Do not begin target measurements until Gemju Sherpa reviews device eligibility and fixture inventory.

14 October 2026: device metadata confirms connected physical iPhone 17 Pro Max/iPhone18,2, iOS26.6.1/build23G83. The friendly device name is not hardware evidence. VC-VERIFY-02 measurement tooling freezes the 20-cold/80-warm question schedule in `packages/voice-latency/tests/turn-plan.json`; acoustic corpus preparation/approval remains pending. No phone latency/endurance/standby pass is inferred. See `packages/voice-latency/README.md`.
