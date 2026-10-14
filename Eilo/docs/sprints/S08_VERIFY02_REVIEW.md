# S08 / VC-VERIFY-02 — acoustic latency evidence prerequisite

Status: partial implementation, awaiting Gemju Sherpa review. **No physical latency measurement or S08 feasibility pass.** Requirements N01/A12; dependencies VC-VERIFY-01 and VC-JOIN-01 remain physically partial.

Gemju Sherpa reviewed/merged PR49 at `1bdc3f9bc7d8a9bd37818631df4e89c9b55dec96`. Final PR49 run38461280611 passed JavaScript, Android and iOS/history. The new sprint/task branches start from that verified merged main.

## Result

Before this checkpoint, the N01 protocol had no reproducible acoustic evidence ingestion/scoring tool. Now `packages/voice-latency/measure.py` verifies local WAV hashes/PCM integrity, exact frozen 100-attempt assignment, and reviewed acoustic frame annotations. The frozen question schedule uses 20 cold and80 warm trials; true speech end to first meaningful audio includes endpointing and excludes filler. SDK callbacks, synthetic endpointing, simulator timings, missing/repeated attempts, reused recordings, inconsistent cold resets, invalid/truncated audio and unknown transcript fields are rejected.

Sorted nearest-rank median/p95 are separate for cold/warm/overall, with1500/3000ms targets. Non-reply outcomes remain counted and prevent target passes; cold failures cannot be hidden in warm/overall aggregation. The tool validates evidence declarations and arithmetic; it cannot establish those declarations are truthful. Its output always requires review. Existing NOT_RUN records have null metrics.

`tests/turn-plan.json` freezes the question/repetition schedule, not a completed acoustic corpus. The actual100 input WAVs and approved hashes remain pending. No production readiness/trust/permission/confidence gate is bypassed, no capture or networking starts, and no additional package/service is installed.

## Checks and reproduction

From repository root:

```sh
python3 -m py_compile Eilo/packages/voice-latency/measure.py Eilo/packages/voice-latency/test_measure.py
python3 -m unittest discover -s Eilo/packages/voice-latency -p 'test_*.py'
python3 -O -m unittest discover -s Eilo/packages/voice-latency -p 'test_*.py'
python3 Eilo/packages/voice-latency/measure.py
```

PASS:20 synthetic regressions in each Python mode. Temporary WAV tests contain no speech and establish schema/arithmetic only. The default real-evidence report remains NOT_RUN for both platforms. Hosted JavaScript CI now runs these same synthetic checks without microphone/models/downloads.

PASS: existing workspace lint/typecheck,9 mobile tests and33 contract tests. Existing React `act` warnings remain in the passing App tests. Same iPhone18 Pro/iOS27 simulator normal Debug build/install plus three fresh ten-second launch checks PASS before commit. This is an app startup check, not a latency test. No native source/adapter changed, so full native unit suites were not unnecessarily repeated.

See `S08_VERIFY02_VALIDATION.json` for evidence, `packages/voice-latency/README.md` for local corpus/report schema and physical collection steps, and `docs/verification/DEVICE_WORKLOAD_MATRIX.md` for the updated device record.

## Physical prerequisites and limits

After reconnection, device details verified physical iPhone17 Pro Max (`iPhone18,2`), iOS26.6.1/build23G83, paired wired connection and Developer Mode. The friendly name mentions a different model; actual hardware details govern. RAM/battery health, exact installed offline voice and reviewed acoustic corpus remain unverified. The physical Android is unavailable.

The normal app still lacks verified production microphone/VAD/joined model/voice attachment. S07 real joined evidence came from recorded fixtures/scripted endpoint/confidence/separation and cannot supply N01 acoustic timing. Installing or opening the normal Home screen would not fix this missing measurement path. The independent acoustic recorder arrangement must be reviewed/calibrated and actual100 trials completed before targets are assessed. Voice/model physical quality gates remain open.

VC-VERIFY-03 interruption timing,60-minute foreground/screen-off,8-hour standby and VC-GATE-04 are not executed or closed. Persistent memory is not started. S08 remains blocked for physical acceptance until prerequisites pass; proposed support configurations remain untested.

## Source control and review

Task `task/s08-vc-verify-02-latency-evidence` → sprint `sprint/s08-latency-evidence` → PR to main for review. Code/checks and simulator startup precede commit. Preserve the three existing personal Xcode/plist/S02 deltas and exclude them from staged files. Main is not merged automatically. Local ignored context/tracker record S07 review approval separately from its incomplete physical/production/semantic gates and keep all175 stable IDs.

Review the question schedule, acoustic annotation rules, conservative handling of non-replies and prerequisite split. Next dependency work is real pipeline/corpus preparation; VC-VERIFY-03 can reuse this evidence approach after its scoped implementation. No deployment or paid services are authorized.
