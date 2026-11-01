# Offline development calibrator pilot

This S05 VC-TURN-06 dependency experiment fits two isolated one-dimensional score mappings. It
does not train or replace the ASR model, change the ordinary app, qualify confidence, select a
threshold or enable production. Existing approved Moonshine/ORT source, model and runtime caches,
Common Voice 26 Australian English data and license/consumer approvals are reused. No download,
new package, microphone, physical device or new terms are involved.

## Frozen method and cohort limits

The only fitting data are the 30 development observations from `../asr-fresh-split/results.json`.
Their private count digest, development manifest and published results are checked before fitting.
Earlier test observations are never fitted. Correctness means normalized exact transcription;
it is a proxy, not semantic usefulness or command safety. Greedy and self-draft paths remain
separate. Tied scores are grouped, weighted PAVA minimizes development squared loss, and a
right-closed upper-step function clamps outside its observed score range. Small empirical blocks
can overfit and predict zero or one; these are candidates, not established probabilities.

The initial protocol sought 30 new test clips from unseen speakers. Archive metadata showed
**zero** eligible unseen dev/test speakers after the prior 90 clips. That selection stopped before
extraction or inference. No train rows were relabeled as test. Before any new inference, the scope
was narrowed and committed as `5f43981ea9ef849940aac85b508d1ccc73e4066c`: new utterances from
known curator-test speakers, while strictly excluding the fitting development speakers and every
prior normalized utterance, encoded-file hash and PCM hash. The fitted model values stayed identical
to the initial candidate; only scope/source provenance changed. The first attempted protocol and
failure remain in Git/local logs. This is **not unseen-speaker validation**. Earlier examination of
the test-speaker population and the small development cohort limit generalization claims.

Selection uses fixed seed 20261027, bounded validated archive members, unique normalized text and
at most two clips per speaker. The actual test contains 30 new utterances from 30 known test
speakers, with zero development-speaker/text/encoded/PCM overlap. Curator train/dev/test speaker
disjointness is checked. Decoder/preprocessing and 30-second limits match prior experiments.
All original 90 cases are excluded by the independent verifier; none is silently replaced after
inference. Model-training overlap remains UNKNOWN. All 120 clean clips examined so far are now
consumed for future experiment planning; this test must not later be fitted and called untouched.

The evaluator requires the exact committed `freeze.json` blob and an ancestor commit before it
invokes the unchanged `../asr-corpus-score/run_android.py` collector. Private model/source hashes
are checked before/after. References never enter native inference; hypotheses are discarded after
in-memory edit counts. Only synthetic file-fed input reaches an explicitly selected audio-disabled
API35 ARM64 emulator. Unique scratch/input files are removed, and the emulator started for this
run is stopped. Total prototype builds remain within the approved 5 GiB budget.

## Observations

Both paths have 29/30 scores available and 23 exact matches among those 29. The unavailable clip
remains in all coverage denominators. WER over available clips is 0.042403 for each path.

| Path | Raw Brier | Mapped Brier | Raw accept/errors at 0.85 | Mapped accept/errors at 0.85 |
| --- | --- | --- | --- | --- |
| Greedy | 0.166346 | 0.087404 | 29 / 6 | 20 / 0 |
| Self-draft | 0.166375 | 0.107983 | 29 / 6 | 20 / 0 |

Mapped coverage is 20/30, not 20/29. Zero observed errors among 20 accepted transcriptions does
not prove zero risk or 85% probability calibration. Four greedy and three draft scores fall outside
the development score range and use endpoint clamping. Brier/ECE/AUROC are conditional on
available scores. The fixed 0.85 cutoff remains descriptive; no test refit or threshold search
occurred. Speech/noise robustness, larger independent cohorts, native streaming/caller integration
and production policy authorization remain unresolved. The ordinary app still has no qualified
confidence signal, S08/release HOLD and persistent memory disabled; physical tests remain OPEN.

## Reproduce and validate

`calibrate.py` consumes the prior ignored development-count file and produces a **private** model
plus public `freeze.json`. Commit that hash before inference. `select_test.py` requires the approved
archive/receipt, all three prior manifests, existing decoder and a new output directory. `evaluate.py`
requires those same prior manifests, the frozen private model, `--freeze-commit`, explicit source,
cache/NDK/CMake/SDK paths and `--serial emulator-5554`. Use new build/output paths. Existing cache
and tool versions are documented in `../asr-fresh-split` and `../asr-corpus-score`; do not fetch
missing prerequisites automatically. The current run used the amended committed scope above.

For the 600-case audit cohort, `select_audit_v2.py` defaults to the pinned `afconvert` interface;
use `--decoder-kind ffmpeg` only with an already approved FFmpeg executable. The chosen kind and
decoder executable hash are recorded in all three private frozen manifests. The selector never
searches for, installs, or downloads a decoder.

After development-only inference, run `evaluate_validation_v2.py fit-development` with the private
attempts, selection inventory and development manifest. It fits separate PAVA models using only the
200-case development phase and writes the knots to the ignored `.local` cache. Then run
`evaluate_validation_v2.py freeze` with that private mapping file and the same development inputs;
it recomputes the fit before writing only the two mapping hashes and source/protocol pins to
`packages/asr-calibration/mapping-freeze-v2.json`. Commit that public freeze before validation
inference. After validation, `evaluate_validation_v2.py evaluate` requires the exact committed
freeze blob, its full commit hash, the frozen selection inventory/validation manifest and local-only
per-case attempts. It computes exact-match labels from local references/hypotheses and emits
aggregate counts only; unavailable scores stay in the 200-attempt coverage denominator. The sealed
audit remains closed unless both validation sources pass. This evaluator does not run model
inference, open the sealed cohort, authorize confidence use, or alter physical/release gates.

From Eilo, without corpus/model/device access:

```sh
python3 -m unittest discover -s packages/asr-calibration -p 'test_*.py' -v
python3 -O -m unittest discover -s packages/asr-calibration -p 'test_*.py' -v
python3 packages/asr-calibration/calibration_report.py --output /new/report
```

Thirteen tests include an exhaustive global monotone squared-loss oracle, weighted ties/order,
step boundaries/clamping, malformed models, missing-score/zero-score distinction, split/overlap
guards, commit/blob checks and report tampering/overwrite denial. CI validates recorded schemas,
pins, arithmetic and synthetic tests; it cannot authenticate native observations, reproduce private
inference or establish training independence. Only aggregate JSON/HTML is uploaded for seven days.
No audio, references, hypotheses, speaker identifiers, case scores or private fitted knots are
committed/uploaded. Existing CC0/MDC restrictions and the retained native MIT notices apply.
