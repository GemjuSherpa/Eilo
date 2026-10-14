# VC-GATE-01 — foreground endurance evidence prerequisite

Partial, awaiting Gemju Sherpa review. Physical60-minute workload NOT_RUN; N06/N08/A12 targets unassessed. Verified iPhone connection does not attach the missing native voice pipeline or produce physical performance evidence.

`packages/voice-latency/endurance.py` accounts for a frozen60-minute workload: one fixed synthetic question per minute,60 turn attempts,61 resource observations at minute0..60, and the final15 turn attempts. Each reply uses checksum-verified independent PCM16 acoustic annotations with true speech end and first meaningful reply. Failed turns stay counted. S01's ten-question catalog is reused; real acoustic corpus remains unprepared. Native process/resource trace hashes and reviewed continuous-capture declarations accompany the sampled observations.

No passing result from a short run, simulator, charging device, increasing battery, missing/out-of-order sample, duplicated recording, shifted cadence or SDK-start timing. INCOMPLETE runs retain observed duration/reason and output FAIL with null full-run metrics. Final15 median≤1500ms/p95≤3000ms, active battery≤15points/hour, peak native RSS<2.5GB and pack<2GB are scored. Crash/thermal shutdown/capture gaps and non-replies fail. Thermal states are reported, not silently converted into a heat-certification claim. Minute samples alone cannot prove no intervening interruption; the independent continuous trace must be reviewed. No actual resource trace has been collected.

Reproduction from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s Eilo/packages/voice-latency -p 'test_endurance.py'
PYTHONDONTWRITEBYTECODE=1 python3 -O -m unittest discover -s Eilo/packages/voice-latency -p 'test_endurance.py'
python3 Eilo/packages/voice-latency/endurance.py
```

Seven focused synthetic regressions PASS in each mode. Tests generate temporary non-speech WAVs and artificial hour traces; no real hour/device workload occurs. Default iOS/Android rows are NOT_RUN. Exact schema fields are documented by `endurance.py` and construction in `test_endurance.py`. A future report uses `--corpus-root` for ignored local recordings; no raw user content, device serial or logs are accepted/committed.

Required same-iPhone18 Pro simulator normal build/install and three fresh ten-second launches precede commit; actual evidence is in `S08_GATE01_VALIDATION.json`. No native adapter/readiness change. Task `task/s08-vc-gate-01-foreground-evidence` → `sprint/s08-feasibility-evidence`; final sprint PR for review; main and personal Xcode/plist/S02 edits preserved.

Physical corpus/recorder/native pipeline/model/installed offline voice review remains open; Android unavailable. Review of this prerequisite does not close VC-GATE-01, authorize persistent memory or establish supported phones.
