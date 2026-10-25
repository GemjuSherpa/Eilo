# S05 VC-TURN-06 dependency — fresh curator development/test evaluation

A fixed protocol and selector were committed before inference. The approved Common Voice 26
Australian English cache supplied 30 fresh development clips (16 speakers) and 30 fresh test
clips (24 speakers), with a two-clip speaker cap and exclusion of the prior 30-case clean/noisy
corpus. Speaker hashes, normalized utterances, encoded-file hashes and PCM are disjoint across
these cohorts and the prior evaluation. Source train/dev/test speakers are also checked disjoint.
Curator splits do not establish absence from model training; repeated speakers may correlate clips.

Actual isolated API35 ARM64 emulator inference found all scores available. Development exact
transcriptions were 19/30 for each path; test was 16/30 greedy and 15/30 self-draft. At the protocol's
fixed 0.85 cutoff development accepts 28 transcriptions with 9 errors in each path. Test greedy accepts
25 with 9 errors (36% accepted-transcription error rate); test self-draft accepts 24 with 9 errors (37.5%).
No threshold fitting occurred, and no policy adjustment or calibration is authorized by this
result. The new cohort resolves reused-data ambiguity for this experiment but does not qualify
production confidence. Separate paths and partitions are preserved, with full missing-score
coverage denominators and conditional error metrics.

The new package `packages/asr-fresh-split` holds the frozen protocol, selective extractor,
independent cohort validator, bounded evaluator, observed aggregate report, strict report exporter
and regression tests. The existing source overlay, model, ONNX runtime and native collector are
unchanged; a new local build verifies their pins. References stay outside the collector; hypotheses
are discarded after in-memory edit counts. Public evidence contains no audio, text, speaker IDs or
case-level scores. CI reproduces only aggregate JSON/HTML and needs no models or datasets.

The first converter attempt failed under the sandbox; the same pinned existing converter succeeded
outside it, with identical selected clips and no substitutions. No new downloads, packages, terms,
account access, physical audio, ordinary-app runtime changes or production activation occurred.
Existing CC0/MDC conditions and retained native MIT notices apply. Physical gates remain OPEN,
S08/release HOLD, memory disabled, model-training overlap UNKNOWN, calibration NOT_ESTABLISHED,
threshold authorization NOT_GRANTED and production NOT_ENABLED. Further qualification and
separately reviewed runtime/caller integration remain open.
