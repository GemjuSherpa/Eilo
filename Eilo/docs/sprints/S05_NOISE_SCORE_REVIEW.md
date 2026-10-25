# S05 VC-TURN-06 dependency — paired noise score diagnostics

The existing frozen 90-case Common Voice/MUSAN suite now has actual isolated Android API35
ARM64 emulator score observations. Each of 30 curator-test utterances has 20, 10 and 0 dB
variants. Every variant was reconstructed sample-for-sample from its pinned clean/noise parents
and deterministic mixing recipe before inference. No dataset/model/source/package download,
physical capture or ordinary-app runtime replacement occurred.

| Condition | Scores per source | Greedy WER available | Self-draft WER available | Greedy accepted/errors at 0.85 | Self-draft accepted/errors at 0.85 |
| --- | --- | --- | --- | --- | --- |
| Clean (previous run) | 29/30 | 0.217573 | 0.217573 | 17 / 4 | 16 / 3 |
| 20 dB | 27/30 | 0.295154 | 0.299559 | 16 / 2 | 16 / 2 |
| 10 dB | 27/30 | 0.342105 | 0.333333 | 13 / 2 | 13 / 2 |
| 0 dB | 25/30 | 0.506912 | 0.497696 | 7 / 3 | 6 / 3 |

WER/Brier/ECE use only available scores, so their populations change across conditions.
Acceptance coverage always uses all 30 cases; errors among accepted answers are normalized
exact-match failures. Missing scores remain unavailable, not zero-valued or omitted successes.
The two decoder paths and repeated parents are correlated. Differences are descriptive, with
no independent-sample significance or monotonic confidence-quality claim. Self-draft receives
the same utterance's greedy hypothesis, no reference, and is not production streaming timing.
The clean run and noise runs share verified model/ORT/source/overlay pins. The native executables
are separately rebuilt from the unchanged isolated collector for each condition.

At 0 dB the 0.85 cutoff accepts wrong answers in both paths (greedy 3/7; self-draft 3/6).
This further identifies a production confidence dependency; it does not validate or adjust that
cutoff. No threshold fitting occurred. The reused small curator test set is not independent
calibration and model training overlap remains UNKNOWN.

The bounded suite runner validates receipt/audio/PCM hashes, parent references/partitions,
noise-only inputs, unique complete SNR pairs, exact mix reconstruction and source consistency.
It invokes the existing maximum-30-case collector separately per level. Temporary subset
manifests and emulator audio scratch are removed; failed partial results remain local for
review. Committed evidence contains only aggregate counts/metrics/hashes. Closed-schema report
validation rejects stale sources/models, modified report bytes, missing conditions, denominator
changes and content additions. JSON/HTML exports refuse overwriting; CI downloads no data and
uploads only aggregate summaries.

Existing Common Voice CC0/MDC conditions and MUSAN component licenses/receipts remain applicable;
no audio, reference, hypothesis, speaker ID or case-level scores are published. This is evaluation
under the previously approved local dataset and prototype permissions. Physical gates stay OPEN
and NOT_RUN for this experiment, S08/release HOLD, memory disabled, calibration NOT_ESTABLISHED,
threshold authorization NOT_GRANTED and production NOT_ENABLED.
