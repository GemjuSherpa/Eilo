# VC-TURN-04 — native VAD probability backend checkpoint

PR62 is reviewed/merged at main 9cf2321 with all eight CI checks passing. The original public
dataset coding tasks are complete; reviewed human time-aligned VAD labels remain unavailable.
This task continues the existing VC-TURN-04 native-backend prerequisite, not another dataset
subtask. It does not mark VC-TURN-04 or S08 physically complete.

A bounded C++17 C ABI now executes the approved Silero v5 ONNX model and returns genuine
window probabilities with sample positions. The existing segment-only sherpa adapter cannot
supply the probabilities expected by EndpointDetector. The core uses the existing pinned ONNX
Runtime 1.28.2 CPU libraries, the upstream 64-sample context/[2,1,128] recurrent-state protocol
and 512-sample/16 kHz windows. No model/runtime downloads or installations occurred.

All failures and finalization terminally revoke a stream; Eilo-owned state/context/scratch is
erased, partial final windows exclude padding from timestamps, borrowed input pointers are not retained (only a bounded 64-sample context is copied),
and exactly 480,000 valid samples is the maximum. Output types/shapes/ranges and finite state
are checked. Runtime/model selection remains the caller's verified native capability; this core
cannot grant trust or application readiness. Vendor allocator erasure remains unverified.

Actual checks:

- Address/undefined-behavior sanitizer contracts PASS: context/state continuity, fresh-stream
  isolation, final padding/counts, post-final/failure rejection, invalid PCM/count/flags/pointers,
  constructor/backend failure, invalid native probability/state, exact 30-second boundary and
  destruction ownership. No models are needed for these scripted backend tests.
- Mac host and the same booted iPhone18 Pro/iOS27 simulator execute the real ONNX model on two
  16,001-sample synthetic-silence streams. Native output repeats exactly; partial final counts
  and post-final rejection pass. This is not classifier accuracy or microphone evidence.
- Host corpus execution: 72 frozen Common Voice/Speech Commands/MUSAN clips, 12,367 native
  windows, all returned finite probabilities with exact valid sample positions. Status
  EXECUTED_UNSCORED, quality NOT_ASSESSED. No F1/miss/false-positive rate is claimed.
- iOS ARM64 device object compilation PASS (not device execution). All four Android ABI object
  builds PASS (not JNI linking, packaging, emulator or phone execution).
- Existing 56 dataset tests pass normal/optimized; registry/compile checks pass. Synthetic CI
  now runs the native sanitizer contracts without model/audio/toolchain installation. Hosted
  native/foundation results must be checked separately on the published PR.

The first iOS probe link attempts exposed the supplied static framework's CoreML/Foundation
link dependencies. CPU remains the only selected execution provider. A later simulator attempt
stalled inside dyld file open under Documents before model code; it was stopped and retried
successfully from checksum-verified temporary executable/model copies. No filesystem/extension
permission was widened, no simulator reset/erase or application activation was performed.

Native windows represent 32 ms, while the existing endpoint policy requires 20 ms scores.
The next prerequisite is a duration-aware bridge and Swift/Kotlin verified lifetime bindings;
do not fabricate 20 ms scores by copying a segment flag or repeating a window probability.
Endpoint thresholds, no-speech timeout, silence policy, confidence, echo separation, trust,
normal capture/readiness and locked/background behavior are unchanged. Normal apps do not
import/link this new package, so no changed-app rebuild applies; native simulator execution and
cross-platform compilation are recorded separately. Original three user edits retain their
exact diff hash and are excluded.

Task task/vc-turn-04-native-vad-probability merges into sprint/native-vad-probability for a PR
to main. Stop for review; no automatic main merge/history rewrite. Physical gates remain NOT_RUN,
production NOT_ENABLED and S08 feasibility remains on hold. No new stable backlog IDs are invented.
