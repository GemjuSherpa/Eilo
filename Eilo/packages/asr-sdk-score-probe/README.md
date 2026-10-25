# Isolated SDK score propagation

This is the S05 VC-TURN-06 dependency follow-up. It instruments the actual pinned Moonshine
v0.1.5 `decode_full` implementation in a verified local overlay. It uses existing source,
NDK27.1, ORT1.23.2 and six synthetic system-voice fixtures on the existing API35 ARM64 emulator.
The immutable source cache, ordinary app runtime and unknown-confidence policy stay unchanged.
No microphone, speaker, phone, network observation, download or package installation is used.

## Native observations

All six fixtures exercised greedy, accepted-draft, accepted-prefix continuation, early-divergence and late-divergence paths.
An independent long-double softmax checks each selected token against its exact captured
pre-bias full-vocabulary row. ContextBiaser still chooses after applying its bonuses. Five
biased paths completed; one biased decode did not reach EOS within its bound and remains
UNAVAILABLE with zero usable partial scores. There are 35 complete diagnostic paths and one
unavailable path, not thirty-six successful scores. Maximum row-oracle difference: 2.94301236e-14.

Fifty-four native fault cases (nine per fixture) produce no usable score: empty memory,
first/continuation decoder errors, missing output, nonfinite logits, output cap, allocation
failure, BOS draft and invalid-vocabulary draft. These include explicit prototype fault
injection; they do not establish the rate of real hardware failures. Guard cleanup discards
all accepted token/score arrays on incomplete/error returns. BOS/EOS are excluded from usable
aggregates; accepted tokens and scores remain one-to-one. Rejected draft suffix scores never
enter the result, and replacements use rows from the actual cache-reset/redecode path.

Repeated identical batch/prefix shapes were stable within 1e-10. The maximum batch-versus-step
probability difference remains 0.145611985; full batch versus truncated-prefix difference is
0.114998032. Cause remains NOT_ESTABLISHED. Token agreement does not make their probabilities
interchangeable. Keep separate source identities for greedy, draft verification and redecoded
rows when any later reference-labelled evaluation is approved. No confidence threshold is fitted.

The initial failed late-divergence assumption is retained in initial-failure.json (source
commit 8a704e8); the following biased completion failure is retained in bias-failure.json
(source commit 8300dfd). Late fixtures now verify the exact teacher-forced accepted prefix
before testing that branch, with a bounded candidate search. Incomplete bias is explicitly
unavailable rather than promoted or removed. Historical source hashes are not refreshed.

## Reproduce offline

The runner accepts the same cache/tool arguments as ../asr-confidence-probe/check_android.py.
Use a fresh --build and --output, --serial emulator-5554, and an already running audio-disabled
API35 ARM64 emulator. It verifies all 696 pinned source files, model files, runtime and fixture
hashes before compilation. The overlay is generated into the new build directory, never into
the upstream cache. Its two hashes must match overlay-expected.json. Upstream CMake/download
scripts are not run. The runner bounds inputs and decode output, refuses overwriting evidence,
checks its build-space cap and removes only its own emulator probe directory in finally.
Keep cumulative experiment builds within the previously approved 5 GiB budget.

Run tests and validation from Eilo:

```sh
python3 -m unittest discover -s packages/asr-sdk-score-probe -p 'test_*.py' -v
python3 -O -m unittest discover -s packages/asr-sdk-score-probe -p 'test_*.py' -v
python3 packages/asr-sdk-score-probe/report.py
```

CI validates the committed native aggregates and pins, hostile evidence mutations, and native
ASan/UBSan math/cleanup contracts. It does not download models/source or independently reproduce
inference. Report files contain no audio, transcripts, token IDs or per-token score arrays.
The invocation-only C++ signature changes belong solely to this overlay and are not a shipping
C API or ordinary-app integration. Existing compiled components are covered by the retained
MIT notices; see ../asr-confidence-probe/SOURCE_REVIEW.md (context biasing is used here).

## Open work

Held-out reference-labelled corpus calibration, source/caller integration and production safety
review remain open. The ordinary app still treats missing/unverified confidence as unknown.
All physical tests remain open as requested. S08/release HOLD and disabled memory are unchanged.

Accepted-prefix cases require a new non-EOS token after a fully verified shorter draft.
The verification_row_scores count includes that first continuation token, whose score comes
from the final verification row, plus accepted draft tokens. Later continuation rows are greedy.
The report validator rejects a missing first-continuation score.
