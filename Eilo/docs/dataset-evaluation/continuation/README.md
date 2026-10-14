# Evaluation continuation

VC-DATA-06 proposes content-addressed diagnostic baseline candidates for independent review.
A fresh 30-clip Speech Commands run reproduced the earlier word/character error counts and
command results exactly: WER 10/30, CER 34/133, overall command accuracy 27/30, target-command
accuracy 6/9. Unknown commands dominate this tiny deterministic subset; it is not a quality gate.
The zero-drift policy is a repeatability diagnostic. Runtime is deliberately excluded because
local startup/verification load varies. Aggregate evidence is in speech-repeat.json.

The original v1 report contains only ASR/command cases. The evidence explicitly records its
content hash and compatibility mapping to v2, whose only scoring change was partial VAD frames.
No VAD score or annotation is migrated. Raw audio, speaker IDs, transcripts and local paths remain
ignored. Physical-device gates stay NOT_RUN and production remains NOT_ENABLED.

The approved Silero v5 model is local only, with MIT license and hash recorded for VC-DATA-07.
Its presence does not establish measured VAD quality: reviewed time-aligned truth is still needed.

VC-DATA-07 adds a file-only native VAD adapter using the already installed sherpa-onnx runtime
and explicitly approved Silero v5 model. The mirror download (2,313,101 bytes) matches the
immutable upstream v5.0 Git blob; SHA256 and pinned MIT license are recorded in vad-provenance.json.
No model weights, corpus audio, transcripts or local configuration paths are committed.

All 72 selected clips executed: 30 Speech Commands, 30 Common Voice and 12 MUSAN. Aggregate
execution reports show detected-duration counts, not accuracy. The MUSAN subset yielded four
segments totalling 4.84 seconds; these need human time-aligned annotation before interpretation.
The weak category labels are deliberately rejected by the scoring runner. Repeated 16,001-sample
native silence checks returned no segments; unit tests cover final-window padding, flush,
clamping, reset/destruction, failures, PCM/duration bounds, and unreviewed model/config rejection.

Remaining gate: reviewed time-aligned speech/non-speech annotations, including ambiguous MUSAN
segments. Physical microphone/session wiring, interruption latency, screen-off behavior, power
and thermal checks remain NOT_RUN. This task neither enables the mobile pipeline nor advances
the S08 feasibility decision.
