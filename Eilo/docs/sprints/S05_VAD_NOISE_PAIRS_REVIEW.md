# S05 paired iOS direct/VAD ASR noise diagnostic

The prior Android direct-score diagnostic bypassed VAD. This increment executes
paired direct-ASR and signed VAD→ASR file replays on the same reviewed iOS framework
and model files. It uses the same 18 approved control prefixes with frozen trailing
silence/minimum-length/cap transformations, plus a known positive question. The
protocol, runner and probe were committed before native execution.

All 18 negative controls returned available empty text in direct ASR. The joined
path ended with noSpeech and no ASR open for 16; two weakly labelled MUSAN clips
completed endpoints and returned available empty ASR text. The six constructed
no-speech controls all ended with noSpeech and no ASR open. The positive question
produced nonempty text in both paths. Native handle opens/closes balance on the
verified worker; the temporary signed lab pack is removed. The relocated client
runs with its original directory absent and a relative Frameworks loader path.

The text measure is nonempty, not lexical correctness. Corpus noise categories
are weak labels, not verified speech absence. The padded iOS inputs/runtime differ
from the earlier raw Android diagnostic; no cross-report treatment effect or
hallucination reduction is inferred. Unavailable results remain unknown in schema
and mutation tests, although the actual collection had none. No confidence scores,
threshold fit, wake-boundary, microphone, LLM or speech workload is introduced.

Validation: actual 19 paired native replays, 25 capture tests, six new optimized
regressions, all offline VC workflow blocks and secret scans. Only aggregate
counters/hashes are committed; no audio, transcript, model or binary is uploaded.
CI validates recorded observations rather than rerunning the native workload.

Physical gates remain OPEN/NOT_RUN, ordinary production NOT_ENABLED, confidence
NOT_EVALUATED, calibration NOT_ESTABLISHED, threshold NOT_GRANTED, full-system
false activation NOT_MEASURED, S08/release HOLD and memory DISABLED.
