# Native speech pack verification — VC-PACK / VC-TURN-04/05

PR68 merged at 57908f6; all eight CI checks passed. Separate manifest, lease and validation task
branches feed sprint/native-speech-pack-leases for one final PR. Main merge remains for human
review. This continues signed model verification without approving production trust/runtime use.

## Artifact contract

Existing signed-pack metadata could not represent Moonshine's evaluated model files. Add only
six exact ORT basenames for role asr (adapter, cross_kv, decoder_kv, encoder, frontend.model and
frontend.weights) and tokenizer.bin for role tokenizer. Existing ordinary filename formats remain
unchanged; arbitrary ORT/bin files, wrong added roles, paths and compound names are rejected.
The eight-file model selection will separately require exact IDs/hash/size/license evidence.
No schema revision, origin/signature/license/readiness relaxation or model download is introduced.

Manifest checks: 281 Swift/334 Android tests PASS; Android lint/Debug/Release compilation PASS;
normal same iPhone18 Pro simulator build/install/three ten-second launches PASS before commit.

## Acceptance boundary

No production trust keys, selected production packs or runtime activation are provided. Slots must
remain app-private and immutable; known maintenance revokes epochs before file changes. This does
not claim arbitrary external mutation detection during an open native call. Wake/question alignment,
calibrated ASR confidence, production capture attachment and physical voice/route/performance gates
remain open. Physical NOT_RUN, production NOT_ENABLED, S08 HOLD, persistent memory denied.
