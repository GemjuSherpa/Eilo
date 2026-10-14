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
