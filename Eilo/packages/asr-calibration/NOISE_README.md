# Frozen calibrator paired-noise diagnostic

See [S05 review](../../docs/sprints/S05_CALIBRATOR_NOISE_REVIEW.md) for methods, observed failures and limitations. `noise-protocol.json` and `noise_pilot.py` were frozen before inference; `noise-results.json` records aggregate evidence. The existing calibrator and clean pilot are unchanged.

Offline validation and aggregate-only export (no corpus/model access):

```sh
python3 -m unittest discover -s Eilo/packages/asr-calibration -p 'test_*.py' -v
python3 -O -m unittest discover -s Eilo/packages/asr-calibration -p 'test_*.py' -v
python3 Eilo/packages/asr-calibration/noise_pilot_report.py --output /tmp/eilo-noise-review
```

Output directories must not already exist. The native runner requires approved local caches and its committed pre-inference protocol; it is not invoked by CI. Repeating or extending inference consumes evaluation data and does not create a fresh holdout. Do not refit on these observations or promote the diagnostic cutoff to production.
