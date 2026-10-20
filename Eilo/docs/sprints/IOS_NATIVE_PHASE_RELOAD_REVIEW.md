# iPhone native phase and repeated reload measurements

This sprint adds opt-in lab instrumentation and records 18 fresh-handle samples per pinned candidate (three rounds of six frozen prompts). Both actual reports validate in normal and optimized Python. The ordinary native adapter and production readiness are unchanged. Full VC-LLM-06 acceptance remains NOT_RUN; S08 remains HOLD and persistent memory remains disabled.

The same connected iPhone was used, with 0.6B first and 1.7B second. Candidate order was not alternated. OS caches were uncontrolled: every sample reloads a fresh handle, so none is asserted to be a true cold-cache or resident-model warm trial. The configured Xcode target is Release with explicit DEBUG and evaluation conditions; this is not shipping Release acceptance.

Native steady-clock intervals distinguish the mmap model-load call, begin tokenization, context/sampler/batch setup, prompt decode (prefill), first sampling call, begin-to-first-token sampling and begin-to-first-piece readiness. The latter includes the ordinary adapter’s next-token decode. Load does not force all mapped weight pages resident; later page faults can contribute to prefill/generation. Instrumentation overhead is included. Verified-open wall time separately includes the lease/descriptor verification path.

Descriptive medians across this fixed 18-sample mixture (milliseconds; not full voice-turn latency or general model-selection evidence):

| Candidate | Native mmap load | Prefill | Begin → first token | Begin → first piece | OS lifetime peak MiB |
|---|---:|---:|---:|---:|---:|
| 0.6B | 122.44 | 6061.13 | 6070.50 | 6097.02 | 524.63 |
| 1.7B | 143.21 | 19706.57 | 19715.99 | 19777.20 | 529.85 |

Per-fixture medians/counts and every raw numeric sample are preserved in `packages/physical-ios-trial/tests/native-phase-summary.json` and `native-phase-device-results.json`. There are only three samples per fixture/candidate. No p95 target or model winner is accepted from this small run. Peak memory is the OS process-lifetime ledger, including preparation, not a per-prompt sampled allocation audit.

0.6B: OS Version 26.6.1 (Build 23G83); physical RAM 12262113280 bytes; battery levels 0.949999988079071 → 0.949999988079071; observed thermal raw states [0, 1]. Battery state, Low Power Mode and monotonic observation times are retained for every sample. USB-connected level observations do not measure energy consumption.
1.7B: OS Version 26.6.1 (Build 23G83); physical RAM 12262113280 bytes; battery levels 0.949999988079071 → 0.949999988079071; observed thermal raw states [1, 2]. Battery state, Low Power Mode and monotonic observation times are retained for every sample. USB-connected level observations do not measure energy consumption.

Signed source/binary/model/derived-wrapper provenance and report checksums are in `native-phase-builds.json`; local check records are in `native-phase-local-validation.json`. Both source task branches and the results task merge into one sprint branch and one final review PR. No new downloads/packages/services were used. No microphone/speaker, generated text export, production pack activation or persistent memory was enabled. Original personal edits were preserved.

Remaining full-protocol gaps include true cold-cache/resident-model warm measurements, alternating candidate order, repeated-output human rubric review, independent traffic verification, energy/endurance and memory auditing, physical Android and explicitly OS-permitted background trials. Historical six-score-per-model quality reports remain separate supporting evidence; their ratings are not silently reused for these new outputs. Simulator and desktop checks do not fill physical acceptance rows.
