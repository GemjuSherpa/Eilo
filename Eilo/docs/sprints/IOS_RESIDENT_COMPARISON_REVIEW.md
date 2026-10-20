# VC-LLM-06 alternating resident-weight comparison

The supporting lab sprint completed 36 actual iPhone samples: six frozen fixtures × two exact pinned candidates × one model-unloaded and two warm generations. Full VC-LLM-06 acceptance remains NOT_RUN; S08 remains HOLD and persistent memory remains disabled. No production readiness changed.

Both models are in the same synthetic signed lab pack. Odd fixtures run 1.7B then 0.6B; even fixtures reverse that order. Every group owns one model and exactly three fresh generation handles/contexts/KV caches/samplers. The first sample calls the vendor loader; the two warm samples reuse only the same generic model object/mappings and report zero vendor-load time. Models are freed between groups. The signed-store lease hashes/checks every descriptor, including warm ones; native reuse also checks file identity and thread setting. Stop/background and all failure paths close work/scopes. The ordinary audited adapter is unchanged.

Cold means the model was not owned by the lab scope at group start; it does not mean a fresh process or flushed filesystem cache. Warm mappings are retained, not pinned in physical RAM, and can page fault. Context/KV/sampler allocation is fresh every time. Native first-token sampling and first-piece readiness remain distinct endpoints; no generated answer or audio is exported.

Descriptive medians across this fixed prompt mixture, in milliseconds:

| Candidate | Condition | Samples | Native load | Prefill | Begin → first token | Begin → first piece |
|---|---|---:|---:|---:|---:|---:|
| 1.7B | Model unloaded | 6 | 139.17 | 18830.52 | 18839.77 | 18898.54 |
| 1.7B | Weights retained | 12 | 0.00 | 19434.81 | 19444.28 | 19504.42 |
| 0.6B | Model unloaded | 6 | 115.64 | 6125.69 | 6135.20 | 6160.67 |
| 0.6B | Weights retained | 12 | 0.00 | 6185.93 | 6194.88 | 6219.98 |

Every per-fixture count/median is retained in `packages/physical-ios-trial/tests/resident-model-summary.json`; all 36 numeric rows are in `resident-model-device-results.json`. There is only one unloaded and two warm samples per fixture/candidate. No general model winner, reliable p95 or full voice-turn target is accepted from this sample size.

The original nominal-only schema-1 trial stopped at THERMAL_LIMIT after six valid samples because the phone stayed fair during a five-minute nominal wait. Its report and original signed build are preserved and validated by the frozen schema-1 validator. The comparison protocol requires observing thermal conditions, not nominal-only execution. The corrected schema-2 policy accepts nominal/fair sample starts, waits below serious before every sample (including warm ones), records each cooldown and retains a five-minute wait limit plus one-hour cooperative run deadline. OS thermal state may change during a sample; before/after observations disclose that limitation.

Observed OS build: Version 26.6.1 (Build 23G83); physical RAM 12262113280 bytes. Thermal raw states: [1, 2]; total recorded pre-sample cooldown 420.59 seconds. OS process-lifetime peak including preparation: 527.92 MiB. The USB-connected battery levels were 1 → 1; these are not an energy-consumption measurement. Timing includes instrumentation overhead and uncontrolled OS cache/page-fault behavior.

An earlier corrected schema-2 run recorded CANCELLED after 25 samples during a cooling pause. Its numeric rows are preserved separately in `resident-interrupted-25-results.json`; the existing lifecycle report does not identify the cancellation cause. Those samples are excluded from the fresh completed-run summaries. The operator confirmed readiness before the fresh run.

The corrected app initially could not install for insufficient storage. After all seven known owned aggregate files were backed up and hash-verified, the operator explicitly approved removing only Eilo Foreground Trial and reinstalling the corrected build. Installation succeeded; the operator completed the required opening/verification before the explicit fixed-input trial launch. Both storage/launch outcomes remain in `resident-retry-build.json` with source/binary/model/wrapper/report checksums. No other app/device data was removed. The lab uses Xcode Release plus explicit DEBUG/evaluation conditions; this does not establish shipping Release performance.

Validation: 31 original ABI scenarios and resident allocation/revocation contracts under ASan/UBSan; both real cached CPU model three-generation probes under network/fork denial; 37 Python tests in normal/optimized modes; strict ordinary/phase/resident Swift paths on device/simulator SDKs; portable schedule contract; actual schema-1 partial and schema-2 complete report validation in normal/optimized modes and CI. Each code task passed 309 Swift tests, normal app build/install and three fresh ten-second simulator launches. Local evidence is in `resident-local-validation.json`. Original personal edits remain exact.

Remaining acceptance requirements include independent traffic observation, human rubric ratings for these new outputs, energy/endurance and memory/privacy audits, physical Android and OS-permitted background trials. Historical quality scores are separate evidence and are not silently assigned to these new generations. No new download/package/service, microphone/speaker use, cloud inference or persistent-memory activation occurred.
