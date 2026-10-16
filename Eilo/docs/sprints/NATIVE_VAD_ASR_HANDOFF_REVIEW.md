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

## Joined capture delivery

The existing native capture APIs accept an optional ASR factory and independent disk-free ASR
capability, denied by default. The worker copies VAD-consumed prefixes before erasing callback
scratch, finalizes ASR before entering the controller lock, then rechecks the exact capturing
permit and both model capabilities before releasing native text. Metadata-only VAD callers stay
available without allocating an utterance owner. Recognition callbacks must only enqueue native
work; text must never be bridged or logged. Existing unknown-confidence policy still clarifies.

Joined validation: 271 Swift and 323 Android tests PASS; Android compiler/lint PASS; normal same
simulator build/install/three ten-second launches PASS. Scripted joined tests prove 10752 exact
samples and 192 samples from the last 320 callback, one final, no ASR for no-speech/EOF, denied
ASR capability, model revocation during cleanup, Stop at accept/final/close and a genuinely blocked
ASR worker without blocking controller Stop. These are scripted ASR tests, not acoustic accuracy.

## Final sprint validation

All three subtasks are complete for a single review PR: bounded prefix ownership, capture/ASR
native delivery, and integrated regression/packaging evidence. Final checks PASS: 271 Swift tests,
324 Android tests (zero failures/errors/skips), Android lint/Debug/Release packaging, normal same
simulator build/install/three ten-second launches, workspace lint/typecheck and nine mobile/33
contract tests. Android native receiver exceptions are mapped to safe unavailable failure without
exporting their causes. All 47 voice-latency tests pass in normal/optimized Python, as do all six
report entry points, 56 dataset tests normal/optimized and the JavaScript CI's simulator/wake/source
integrity fixtures. Existing unrelated Jest act warnings remain; no test suppression was added.

Actual approved VAD regression on both iOS simulator and macOS host JVM/JNI opens/closes five
streams and makes 161 model calls per platform. Quiet input takes the optional handoff path,
retains exactly 80000 samples, opens ASR zero times and clears owned audio; short EOF and Stop/
cleanup regression still pass. Positive ASR uses scripted backends in native unit tests; real ASR
acoustic accuracy is not inferred. Normal APKs and iOS binaries contain no evaluation model/
ASR/VAD activation. Source/model/artifact hashes and scope are in vad-runtime/tests/asr-handoff-*.json.
The changed iOS capture policy source pin is refreshed after verifying observations still apply;
physical gates, HOLD, empty supported configurations and denied persistent memory are unchanged.
No downloads, installs, OS microphone activation or dependency/config changes were introduced.
Temporary existing dependency links are removed after checks; original personal diff is identical.

## Acceptance boundary

PCM remains exactly 16 kHz; unsupported routes fail closed. No streaming route converter,
production signed-pack/runtime caller, wake/question alignment proof or confidence is added.
ASR is opened after endpoint completion, so this bounds ownership without claiming streaming
recognition latency or meeting physical latency/memory targets. Physical voice/route/latency/
battery/background/endurance and Android ART capture remain NOT_RUN. Production NOT_ENABLED;
S08 HOLD and persistent memory denied. Original personal edits remain excluded.

Secret scanning identified the IOSConsentAuthentication.swift source SHA-256 in the native
regression report as a generic API-key pattern. Verified it equals the source-file digest, then
added an allowlist restricted to this report, exact source path and 64-hex checksum line. No
credential rule is disabled or broadly excluded; history scanning passes with this narrow match.
