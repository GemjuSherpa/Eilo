# Direct-ASR negative controls

See [S05 review](../../docs/sprints/S05_NEGATIVE_CONTROL_REVIEW.md). This runs the unchanged isolated native collector on existing MUSAN clips and deterministic synthetic silence/noise, applying the existing frozen calibrator without fitting. The protocol and wrapper were committed before inference. VAD is bypassed; system false activation is not measured.

Offline validation/export (no corpus/model access):

```sh
python3 -m unittest discover -s Eilo/packages/asr-calibration -p 'test_*.py' -v
python3 -O -m unittest discover -s Eilo/packages/asr-calibration -p 'test_*.py' -v
python3 Eilo/packages/asr-calibration/negative_report.py --output /tmp/eilo-negative-review
```

The export directory must not exist. The native runner requires an approved local model/source/data cache, the committed protocol/core, and an owned API35 ARM64 emulator with audio disabled. It is never invoked by CI. Its public report contains only grouped observations and provenance hashes; private counts and fitted values remain local. Do not interpret unavailable scores as no text, MUSAN categories as verified speech absence, or the fixed cutoff as production authorization.
