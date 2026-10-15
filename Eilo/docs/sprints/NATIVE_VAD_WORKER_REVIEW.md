# Native VAD worker integration sprint

PR64 is reviewed/merged at main c5a3128 with all eight CI checks passing. Gemju Sherpa explicitly
authorizes completing the sprint's subtasks on separate branches, merging each into this sprint
and opening one PR at the end. Main merge remains for human review. Existing stable IDs remain;
this continues VC-TURN-04 rather than creating more public-dataset tasks.

| Subtask | Branch | Result |
| --- | --- | --- |
| Native Swift/Kotlin owners and opaque JNI | task/vc-turn-04-vad-lifetime-bindings | Implemented; checks below |
| Bounded PCM window delivery | task/vc-turn-04-vad-window-delivery | Implemented; checks below |
| Joined native runtime validation | task/vc-turn-04-vad-worker-validation | Complete for review |

The first subtask validates local paths, model/controller leases before and after opening and
processing, probability ranges, exact sample positions/counts and final flags. Finalization,
backend failure, revocation and close destroy native state idempotently on the inference worker.
Kotlin loads only explicitly verified libraries; defaults remain unavailable. JNI uses monotonic
opaque IDs, copied/cleared PCM scratch and invalid-handle rejection; native pointers never cross JS.
Normal apps compile the interfaces but load no new runtime/model by default.

First-subtask validation: 236 Swift tests and 286 Android tests PASS; Android compilation/lint PASS.
Host JNI and four Android ABI shared libraries link using the existing pinned runtimes/toolchain;
this is not Android device/JNI execution. Normal same-iPhone18 Pro simulator Debug build/install
and three fresh ten-second launches PASS before commit. No dependencies/downloads installed.
All raw binaries/models stay ignored. Final checks and joined execution are recorded below.

Physical gates remain NOT_RUN, production NOT_ENABLED and S08 feasibility remains on hold.
Trusted pack/capture/ASR confidence/echo separation/background policies are not weakened. Original
personal Xcode/plist/S02 edits remain in the original checkout and excluded from this isolated clone.

The delivery subtask copies at most one 512-sample pending window on its single worker, accepts
bounded sequence-addressed PCM chunks, opens one backend lazily, and never pads an intermediate
window. The five-/thirty-second budgets produce true 128-/256-sample final windows. A completed
endpoint can consume only a prefix of its last callback; consumedSamples explicitly reports that
prefix for downstream ownership. Input discontinuity, malformed backend metadata, revocation,
failure/EOF/close clear pending storage and terminally close the owner. Early EOF remains INCOMPLETE.
Capture callbacks must enqueue elsewhere; this API does not perform inference on a recorder callback.

Delivery validation: final 245 Swift and 295 Android tests PASS, compiler/lint and the same normal
simulator build/install/three ten-second launches PASS. Nine new delivery tests per platform cover
sample ordering, borrowed-buffer mutation, exact budgets/tails, prefix accounting, lazy open,
duplicate/invalid input and revocation during open/inference/final cleanup. Joined runtime validation
is recorded below; no intermediate task PR was created.


## Final sprint outcome

All three scoped subtasks are implemented and merged into the sprint for one review PR.
Actual iOS-simulator Swift and macOS JVM/JNI Kotlin workers execute the approved model through
the same ownership, 320-sample/irregular-chunk buffering and endpoint path. Each platform opens
and closes five worker-owned streams and performs 317 worker-scoped model calls. Quiet/irregular
input ends at exactly 80,000 samples, seven-sample EOF remains INCOMPLETE, and revocation during
actual inference or final cleanup releases no stale result. Direct JNI guard checks additionally
reject old IDs, never reuse a closed ID for a new stream, and revoke invalid-count streams.
Android ABI shared libraries all link; Android ART/phone execution remains NOT_RUN because no
Android target is attached. No emulator/device result is substituted with host-JVM execution.

Final checks PASS: 245 Swift cases; 295 Android cases (no failures/errors/skips), native compiler/
Android lint; normal Debug/Release Android packaging; final normal iPhone18 Pro/iOS27 build,
install and three fresh ten-second launches; workspace lint/typecheck, nine mobile and 33 contract
tests; 56 dataset tests normal/optimized; native ASAN/UBSAN contracts; Python compile checks.
Normal Android APKs contain no evaluation VAD library/model; normal iOS has no VAD C imports or
ONNX weights. Source/model/binary hashes and aggregate execution/packaging evidence are recorded
under packages/vad-runtime/tests. No audio, weights, raw traces, personal identifiers or paths
are committed. Hosted CI remains separately reported on the final review PR.

The initial local Release packaging attempt could not resolve shared symlinked dependencies in
Metro. A temporary local resolver/init file used the already installed dependencies and this
clone's workspace packages; the successful Release retry changed no committed Metro/Gradle
configuration and installed nothing. Existing cache links were temporary and are removed after
validation. Original three personal edits retain their exact diff hash and remain excluded.

## Remaining acceptance boundary

The native worker is ready for review, not automatically attached to normal microphone capture.
A production capture/turn owner must provide the verified model/controller capabilities and
bounded worker transport, honor consumed prefixes, and schedule worker cleanup on Stop even if
no further frames arrive. Signed production trust, ASR confidence, echo-separated user evidence,
offline-voice readiness and permitted background/locked behavior remain their existing gates.
Public VAD accuracy still requires human time-aligned annotations. No feasibility/support,
physical latency, interruption/endurance/standby or persistent-memory approval is inferred.
All physical gates remain NOT_RUN, production NOT_ENABLED and S08 remains on hold.
