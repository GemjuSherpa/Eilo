# Android capture to local reply evaluation

The explicit API 35 ARM64 emulator now runs the actual signed VAD/ASR → signed local Qwen3-1.7B CPU inference → non-thinking output filter → speech policy → native clause queue path. Two invocation modes are evaluated: asynchronous synthetic clause events, and the existing installed offline Android speech SDK with gain zero. Both run without microphone capture. SDK callbacks do not prove audible output or acoustic quality.

The evaluator builds only from the already approved llama.cpp 8345f333951c661d166b00e6f9362e553768f292 source archive and 1.7B Q4_K_M model. It verifies the entire source tree, archive/model digests, CPU-only options and absence of inference archive network clients. Speech uses the existing verified Moonshine runtime and locally converted Silero ORT model established by the preceding ART installer task. Local ORT serialization produced different derived digests and an eight-byte size variation between runs; the original model, converter, runtime and conversion options are unchanged. Each signed pack/report pins the actual derived bytes for its own run; bit-identical conversion is not claimed.

An ephemeral ES256 lab pack holds all three model roles. Controller readiness and microphone permission are synthetic; the evaluation APK has neither Internet nor microphone manifest permission. Native calls run on the named inference worker. The invocation-only source set is removed by rebuilding the normal APK, which is inspected and reinstalled afterward. No models, libraries, source headers, fixture audio or raw inference text are committed.

The following three cases passed in both ART modes:

- `speech16`: real VAD/ASR recognition starts one local reply, the output passes policy and two clauses complete through each mode’s sink. Volatile context holds one user/assistant pair.
- `followup48`: the repeated-sample 48 kHz fixture normalizes and recognizes the same transcript; another local reply completes with two pairs in volatile context. Duplicate submission is rejected in both reply cases.
- `quiet`: no recognition, LLM job or clause begins; prior volatile context is retained until the conversation is explicitly ended.

The offline evidence validator requires exact field/case inventories, per-run source/report pins, approved model/runtime provenance, unchanged vendor binary hashes, sample counts and transcript digests, worker execution, cleanup, normal APK restoration and explicit synthetic/nonphysical scope. Adversarial tests reject acceptance promotions, malformed counts, model/vendor/build changes, extra content fields and ambiguous/oversize JSON. CI evaluates reports without model downloads or native execution.

Regression validation: 380 Android tests and normal lint/build/release Kotlin compile; 325 Swift tests and normal simulator build/install/three launches. Existing workspace lint/types and 58 mobile, 33 contract and 27 search tests passed on the same app source tree in the preceding ART installer task; this task changes only invocation-only evaluators, reports, validation and documentation. Full synthetic workflow blocks pass, including 12 capture/evidence and four SDK tests under both normal and optimized Python.

The SDK prerequisite was also tested independently: an already installed English voice reported no network requirement and produced exactly one start and one finish callback for a fixed muted clause. No package or voice download was requested. A separate report and source inventory record this SDK test. The joined SDK mode then ran both generated replies through the same real adapter, registry, clause queue and completion callbacks. The synthetic-sink baseline remains separately recorded, rather than relabelled as SDK evidence.

The normal APK's Internet/microphone permissions are restored after each evaluation. Removing the evaluation app’s Internet permission does not isolate the speech engine’s separate process; network acceptance remains NOT_RUN. Gain zero and the emulator’s no-audio configuration mean no audible-output acceptance is claimed.

The ordinary app pipeline remains disabled. Synthetic confidence 0.95 is not acoustic calibration. Installed-voice readiness and muted Android SDK callbacks are demonstrated in this emulator. Microphone capture, audible output, actual audio-stop timing, acoustic interruption separation, network behavior, physical-device and release acceptance remain NOT_RUN or blocked by their existing prerequisites. S08/release HOLD and persistent memory disabled are unchanged.
