# S05 VC-TURN-06 dependency — curator-test score diagnostics

The approved existing Common Voice 26 Australian English frozen test set (30 cases) now has
native score diagnostics from an isolated v0.1.5 file-fed emulator collector. No model/runtime
upgrade, dataset download, physical capture or threshold fitting occurred.

| Source | Available | Exact matches among available | WER available | Brier | ECE | Accepted at 0.85 | Errors among accepted |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Greedy pre-bias mean | 29/30 | 14/29 | 0.217573 | 0.271869 | 0.368032 | 17/30 | 4/17 |
| Same-utterance self-draft pre-bias mean | 29/30 | 14/29 | 0.217573 | 0.269090 | 0.366859 | 16/30 | 3/16 |

One greedy observation reached EOS without usable aligned scores; its self-draft dependency
was unavailable. Both remain in the 30-case coverage denominator. Error metrics are conditional
on available/accepted scores. The two sources are paired, correlated and not pooled. Curator
test membership does not establish absence from model training, and this small reused set is
not independent production calibration. Neither path validates the existing 0.85 policy gate.

The collector receives only model/audio paths. References remain in the offline parent and
hypotheses are discarded after normalized edit-count scoring. Committed/exported evidence has
only aggregate metrics and hashes, with no text, speaker identifiers or case-level scores.
Closed-schema validation checks metric arithmetic, missing-case denominators and source/model
pins. JSON/HTML report reproduction and retained MIT notices are under packages/asr-corpus-score.

All physical tests remain open under the user's instruction. Native calibration remains
NOT_ESTABLISHED, threshold authorization NOT_GRANTED and production NOT_ENABLED; S08/release
HOLD and disabled memory remain. This is measured diagnostic evidence, not closure of the
production VC-TURN-06 gate. Future work needs broader independent evaluation and a separately
reviewed runtime/caller integration; no new permissions or dependencies were required here.
