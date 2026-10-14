# VC-VERIFY-03 — interruption evidence prerequisite

Partial implementation, awaiting Gemju Sherpa review. Physical N02/A05/A12 timing NOT_RUN. Dependencies VC-VERIFY-01 and VC-JOIN-03 remain physically partial. PR50 merge96e3553 and all final checks verified; remaining S08 work is authorized continuously with separate task branches.

The new `packages/voice-latency/interruption.py` computes nearest-rank p95 from reviewed same-recording acoustic frames: intelligible user onset to final old audible playback. SDK cancellation is rejected. A frozen100-attempt schedule varies early/middle/late clause positions;20 synthetic non-directed/noise controls are an additional conservative prerequisite. These questions/positions are frozen, but acoustic input corpus preparation/approval remains open.

All100 interruption attempts and20 noise controls must remain in the report. MISSED/CANCELLED, old-audio resumption and false triggers prevent target passing even when the successful-stop p95≤300ms. At least one second of post-onset acoustic observation is required to look for resumption; later stale output remains a separate lifecycle audit. Each attempt needs a distinct checksum-verified PCM16 recording, exact physical configuration, offline/native-pipeline declarations and Gemju Sherpa annotations. This validates shape/arithmetic, not truth, semantic speaker separation, privacy or audible correctness.

Reproduce from repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s Eilo/packages/voice-latency -p 'test_interruption.py'
PYTHONDONTWRITEBYTECODE=1 python3 -O -m unittest discover -s Eilo/packages/voice-latency -p 'test_interruption.py'
python3 Eilo/packages/voice-latency/interruption.py
```

Six focused synthetic regressions PASS in both modes. The default physical records remain NOT_RUN with null p95; no measured samples. Input schema is documented by the exact allowlisted keys in `interruption.py` and synthetic construction in `test_interruption.py`; run a future report with `--corpus-root` pointing to ignored `.local` independent acoustic recordings. Do not use unit-test WAVs as corpus: they contain no speech. The frozen plan and hashes do not establish actual physical collection.

Required normal same-iPhone18 Pro simulator build/install and three fresh ten-second launches run before commit; task evidence records actual results. No adapter/source/readiness change. Physical iPhone17 Pro Max remains connected; app native capture/VAD/independent separation/model/offline-voice attachment is unavailable. No Android phone. Neither platform's physical interruption target is assessed.

Task `task/s08-vc-verify-03-interruption-evidence` merges to `sprint/s08-feasibility-evidence`; final S08 PR is for review, no automatic main merge. Personal Xcode/plist/S02 edits excluded. Next work: foreground, screen-off and standby evidence without fabricating long-run trials.
