# Fresh curator development/test score diagnostics

This is an isolated local evaluation of the approved pinned Moonshine v0.1.5 source overlay,
existing English model and ONNX runtime. It does not replace the ordinary app's ASR runtime or
enable confidence. Common Voice 26 Australian English and the existing CC0/MDC approval are
reused; no download, package installation, microphone, physical-device test or new terms.

## Frozen method

`protocol.json` and the selection/evaluation code were committed before inference. Selection
reads the already approved local archive after checking its receipt/checksum. All archive names
are validated before selective extraction; links/devices, duplicate paths, traversal and
oversized members are rejected. The source curator train/dev/test speaker sets must be disjoint.
Only selected dev/test MP3 files and their minimal metadata are extracted into the ignored local
cache. The train partition is used for split-overlap checking, never inference or training.

The prior 30-case clean/noisy evaluation's speakers (using the same SHA256 client-ID transform)
and normalized utterances are excluded. Development selection precedes test selection, with
fixed seeded path ordering, two rounds, at most two clips per speaker and unique normalized
utterances across both cohorts. Counts are fixed at 30 development/30 test. There are 16 and 24
speakers respectively. The evaluator independently checks speaker/text/source-file/PCM disjointness
against the prior corpus and across cohorts, hashes, proper validation/test labels, counts and
speaker cap. No failed or inaccurate clip is replaced after evaluation.

The existing pinned `/usr/bin/afconvert` path and deterministic PCM preprocessing freeze mono
16 kHz audio; 30-second duration caps reject possible truncation. The sandbox's converter failure
was retained locally, then the identical selection was re-frozen with the already approved local
converter outside that sandbox. All source/helper/model/ORT/overlay pins are verified, and the
unchanged C++ collector is rebuilt locally. A fresh isolated scratch directory on the explicitly
selected audio-disabled API35 ARM64 emulator contains only file-fed inputs. No app replacement,
network inference or hardware audio is used. Each call has a 120-second remote/180-second host
bound and 128-token output cap. Only this experiment's scratch and temporary float input are
removed in finally; build/output paths must be new. Keep cumulative experiments under 5 GiB.

References never enter the collector. Hypotheses remain in memory only until normalized
edit-count scoring, then are dropped. Private progress contains case IDs/counts/scores without
text or speaker IDs; public `results.json` contains only closed-schema aggregates and hashes.
Same-utterance self-draft receives the greedy hypothesis without the reference and is not
production streaming timing. Paths remain separate. Two clips per speaker may be correlated;
curator partitioning does not establish model-training exclusion or independent calibration.

## Observations

| Partition / source | Available | Exact transcriptions | WER available | Brier available | Accepted/errors at fixed 0.85 |
| --- | --- | --- | --- | --- | --- |
| Development / greedy | 30/30 | 19 | 0.063291 | 0.295999 | 28 / 9 |
| Development / self-draft | 30/30 | 19 | 0.063291 | 0.295265 | 28 / 9 |
| Test / greedy | 30/30 | 16 | 0.092150 | 0.348740 | 25 / 9 |
| Test / self-draft | 30/30 | 15 | 0.095563 | 0.369613 | 24 / 9 |

An error here means any normalized exact-match failure. Low WER can coexist with many imperfect
transcriptions. Metrics use available scores; coverage retains every selected case, including unavailable
scores if any. All four invalid native inputs (empty, unaligned, NaN, out-of-range) were rejected.
The predeclared 0.85 cutoff is descriptive. No threshold fitting/selection occurred on either
partition. Test results were examined after the frozen protocol and native evaluation completed.
High-scoring incorrect transcriptions remain; do not treat available scores or passing tooling tests as
calibration, policy acceptance or a production-ready clarification signal.

## Reproduce

Use only the already-approved caches/tools. Run `select_split.py` with absolute `--archive`,
`--receipt`, `--prior`, `--output` and `--decoder` paths; output must not exist. The prior manifest
is the existing 30-case Common Voice frozen manifest. No new source/audio fetch is performed.
Then `evaluate.py` requires `--cohorts`, `--prior`, `--source`, `--cache`, `--build`, `--ndk`,
`--android-sdk`, `--cmake`, `--output` and `--serial emulator-5554`. Tool/cache paths match
`../asr-corpus-score/README.md`. Run against an already running audio-disabled emulator only.

From Eilo, validate without corpus/model access:

```sh
python3 -m unittest discover -s packages/asr-fresh-split -p 'test_*.py' -v
python3 -O -m unittest discover -s packages/asr-fresh-split -p 'test_*.py' -v
python3 packages/asr-fresh-split/fresh_report.py --output /new/aggregate-only-report
```

The JSON/HTML exporter refuses overwriting and rejects content additions, stale pins, overlapping
cohort claims, partition relabeling, denominator/metric errors and acceptance promotion. CI uses
committed aggregates without datasets/models and uploads only these two summary files. It
checks schema/arithmetic/integrity, not the truth of native observations or physical behavior.
The Moonshine/ORT/nlohmann notices already retained in `../asr-corpus-score/licenses/` apply to
the unchanged isolated executable. Common Voice CC0/MDC restrictions prohibit speaker
identification and rehosting; no audio/text/speaker identifiers/case-level scores are published.

Physical gates stay OPEN, S08/release HOLD and memory disabled. Model training overlap UNKNOWN,
native calibration NOT_ESTABLISHED, threshold authorization NOT_GRANTED and production NOT_ENABLED.
