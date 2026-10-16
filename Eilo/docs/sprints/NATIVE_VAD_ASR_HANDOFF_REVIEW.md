# VC-TURN-04/05 — bounded VAD-to-ASR audio handoff

PR66 is merged at e904624 with all seven checks passing. This sprint continues the existing
native endpoint/ASR tasks on separate task branches merged into sprint/native-vad-asr-audio-handoff,
with one final review PR. Production readiness and physical acceptance remain separate gates.

## Bounded prefix owner

VadAsrHandoff is confined to one native inference worker. It copies only VAD's consumed prefix
from <=1600-sample chunks, rejects gaps/duplicates/invalid samples or totals above 480000, and
erases its fixed buffer on terminal completion/failure/close. The maximum owned PCM is 1.92 MB
(30 seconds of Float32 at 16 kHz); allocation and erasure occur on the worker. Silence at exactly
80000 samples and incomplete EOF discard audio without opening ASR or producing text.

For complete/capped utterances only, the exact prefix is fed to StreamingAsr in <=1600-sample
borrowed chunks, finalized once and closed. Token/model capabilities are checked before/after
accept, final text and backend cleanup. Native text is never a JS/diagnostic/file payload. Android
accepts already-normalized Float32 without requantizing it to PCM16. Unknown confidence is not
invented; existing recognition/echo policy remains responsible for interpreting final text.

Prefix-owner validation: 266 Swift and 318 Android tests PASS; Android lint/Debug and Release
compilation PASS; same iPhone18 Pro simulator normal build/install/three fresh ten-second launches
PASS. Tests cover exact last-callback prefix, borrowed-buffer mutation, silence/EOF suppression,
30-second cap/overflow, invalid sequence/metadata and revocation during accept/final/cleanup.

## Acceptance boundary

PCM remains exactly 16 kHz; unsupported routes fail closed. No streaming route converter,
production signed-pack/runtime caller, wake/question alignment proof or confidence is added.
ASR is opened after endpoint completion, so this bounds ownership without claiming streaming
recognition latency or meeting physical latency/memory targets. Physical voice/route/latency/
battery/background/endurance and Android ART capture remain NOT_RUN. Production NOT_ENABLED;
S08 HOLD and persistent memory denied. Original personal edits remain excluded.
