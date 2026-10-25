# Common Voice score diagnostics

This S05 VC-TURN-06 dependency follow-up evaluates the existing approved frozen 30-case
Common Voice 26 Australian English curator test manifest. It is an offline API35 ARM64
emulator experiment, using the verified Moonshine v0.1.5 overlay from asr-sdk-score-probe,
existing NDK27.1/ORT1.23.2 and existing English streaming weights. It does not replace the
ordinary app runtime, open microphone/speaker hardware, download anything, or run phone tests.

## Two score sources

GREEDY_PREBIAS_MEAN_V1 is the arithmetic mean of selected non-EOS token probabilities from
actual decode_full greedy rows. SELF_DRAFT_PREBIAS_MEAN_V1 uses that same utterance's greedy
hypothesis as a draft, then scores actual verification/redecode rows. It is an offline
self-draft diagnostic, not a simulation of production streaming draft timing. References are
never passed to the native collector. The paired sources are correlated and never pooled.

The collector validates complete aligned token/score arrays and the exact pre-bias row oracle.
A non-EOS token cap, error, empty output or otherwise unusable alignment yields no score.
The parent normalizes hypotheses/references with existing nfkc-casefold-alnum-v1 and computes
word/character edit counts in memory. Hypotheses are read only from the invocation pipe and
never written by the runner. Private progress/completed files contain anonymous case IDs,
counts and scores only; no text, speaker IDs, raw audio or original clip paths.

## Recorded result

Both sources produced scores for 29/30 cases, with 14 exact normalized matches among those 29.
The greedy unavailable observation reached EOS without usable scores; its self-draft remained
unavailable because the prerequisite greedy hypothesis was unavailable. Neither is silently
removed or assigned fake zero confidence. WER/CER are conditional on the 29 available cases:
0.2175732218 / 0.1224818695 for both paths. This is not a full-corpus WER or a quality PASS.

At the pre-existing descriptive 0.85 threshold, greedy accepted 17/30 cases with four errors
(risk 0.2352941176); self-draft accepted 16/30 with three errors (risk 0.1875). These small,
reused curator-test results do not validate a threshold or demonstrate model-training exclusion.
Brier/ECE/AUROC are descriptive over available scores only. All 101 fixed thresholds retain
30 as the coverage denominator. No threshold is fitted, selected or authorized.

The aggregate JSON contains separate source identities, unavailable reasons, score moments,
correctness pair counts, reliability bins and the fixed threshold grid. CI checks Brier/ECE/AUROC
and denominator arithmetic against those aggregate sufficient statistics. Runtime/model/overlay,
registry, manifest and private-count hashes bind the recorded run, but CI does not download the
corpus, reproduce inference, authenticate observations or prove training independence.

## Integrity, license and privacy

The runner validates the frozen public-corpus receipt, test partition and every WAV/PCM hash.
It rejects train/validation/synthetic inputs and more than 30 cases, clipping/resampling and
oversized/changed inputs. All model files and the original 696-file source inventory are
verified before compilation; the overlay writes only to a fresh build directory. The immutable
upstream cache and normal app stay unchanged. Inputs are at most 30 seconds, output at most
128 tokens, and each remote invocation is bounded by timeout. Existing output/build directories
are rejected. Only the explicitly selected API35 ARM64 emulator is allowed. Its unique scratch
is removed in finally, including the temporary float input, while normal installed apps remain.
Keep cumulative prototype builds within the approved 5 GiB budget.

Common Voice is CC0-1.0 with the previously approved MDC terms: no speaker identification or
rehosting. No audio, references, hypotheses, speaker IDs or case-level data are committed or
uploaded. The dataset registry/receipt and public source URL are documented in
../dataset-evaluation/README.md. Core/model/ORT and nlohmann MIT notices are retained under licenses;
only the previously reviewed minimal ASR source subset is compiled. No new terms are accepted.

## Reproduce and validate

Use run_android.py with absolute --source, --cache, --manifest, --build, --ndk, --android-sdk,
--cmake and --output paths, plus --serial emulator-5554. Source/cache/tool arguments match
../asr-sdk-score-probe/check_android.py; --manifest is the ignored existing frozen manifest.
Run only on an already running audio-disabled emulator. This writes a new aggregate report.

From Eilo:

```sh
python3 -m unittest discover -s packages/asr-corpus-score -p 'test_*.py' -v
python3 -O -m unittest discover -s packages/asr-corpus-score -p 'test_*.py' -v
python3 packages/asr-corpus-score/report.py --output /new/aggregate-only-directory
```

The exporter refuses overwriting, validates closed schemas and creates JSON/HTML without content
or case identifiers. CI validates the committed report and protocol/math/privacy regressions
without downloading data or performing capture.

Model-training overlap remains UNKNOWN, native calibration NOT_ESTABLISHED, threshold authorization
NOT_GRANTED and production NOT_ENABLED. Physical tests remain open as requested; S08/release HOLD
and disabled memory are unchanged. Wider independent evaluation and reviewed runtime/caller
integration remain prerequisites for production confidence acceptance.
