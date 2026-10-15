# Native VAD worker integration sprint

PR64 is reviewed/merged at main c5a3128 with all eight CI checks passing. Gemju Sherpa explicitly
authorizes completing the sprint's subtasks on separate branches, merging each into this sprint
and opening one PR at the end. Main merge remains for human review. Existing stable IDs remain;
this continues VC-TURN-04 rather than creating more public-dataset tasks.

| Subtask | Branch | Result |
| --- | --- | --- |
| Native Swift/Kotlin owners and opaque JNI | task/vc-turn-04-vad-lifetime-bindings | Implemented; checks below |
| Bounded PCM window delivery | task/vc-turn-04-vad-window-delivery | Implemented; checks below |
| Joined native runtime validation | task/vc-turn-04-vad-worker-validation | Planned |

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
All raw binaries/models stay ignored. Later subtasks will record final checks and joined execution.

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
is the final planned subtask; no intermediate task PR is created.
