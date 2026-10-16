# Native VAD probability core — VC-TURN-04 continuation

The C++17 C ABI runs the already approved MIT Silero v5 model through the installed ONNX Runtime
1.28.2 CPU backend. It produces actual floating-point model probabilities, not segment-state flags
or scripted scores. The model tensor contract follows the [pinned upstream v5.0 wrapper](https://raw.githubusercontent.com/snakers4/silero-vad/5cd2ba54db059f961e7545d4f211b44f005a6dfb/utils_vad.py):
512 samples at 16 kHz, 64 preceding context samples and recurrent state shaped [2,1,128].
Inputs/outputs and model/runtime/build inputs are pinned and validated for local evaluation.
No vendor source or binaries are copied into the repository.

The stream takes 512-sample nonfinal frames and an explicitly final frame of 1–512 samples.
Only the last window is zero padded; reported start/count exclude padding. The 30-second cap
counts actual PCM samples. Input must be finite mono floats in [-1,1]. Invalid input, backend
failure, invalid probability/state or finalization terminally revokes the stream. There is no
reset that can revive a revoked stream. Eilo-owned context/state/scratch clears on failure,
finalization/destruction; the caller owns borrowed PCM. Vendor internal allocator erasure remains
unverified. Calls and destruction must be serialized by one inference-worker owner.

This is an evaluation core, not an app-ready VAD attachment. The C ABI caller must provide a
verified native model capability and preserve controller/model leases before/after inference.
No trust key, manifest, model-readiness, capture permission, confidence or echo gate is added or
weakened. Normal apps compile the interfaces but do not link or activate the native evaluation runtime by default. No microphone, network,
downloader, runtime installation or application launch occurs in these checks.

**Timing boundary:** native probabilities cover 512 samples (32 ms). The legacy EndpointDetector API
expects 320-sample (20 ms) probabilities. Do not duplicate a probability into multiple 20 ms
frames or use segment detection as a probability. The duration-aware receiver and explicit lifetime/worker bindings are described below. Production
capture attachment still requires its own verified native caller. Endpoint thresholds and
interruption policy are not bypassed.

## Reproduce

Run sanitizer contracts without models or vendor headers:

```sh
python3 Eilo/packages/vad-runtime/check_contract.py
```

Run the approved artifact with existing toolchains/cache (no downloads):

```sh
python3 Eilo/packages/vad-runtime/check_native.py --cache /local/existing/kws \
  --model /local/approved/silero_vad_v5.onnx --output /local/new-vad-evidence \
  --manifest /local/frozen/manifest.json \
  --ios-simulator E01AE333-A393-48F6-AAD7-579F0A5DB1F8 \
  --ndk /local/existing/ndk/27.1.12297006
```

The tool verifies the approved model hash, published iOS runtime archive checksum, framework
artifacts and host headers/library before compilation/inference. It checks the same booted iPhone
18 Pro simulator before execution and does not create, erase or install an app. iOS device and
four Android ABI object builds are compilation only, not phone execution or packaged JNI checks.
Temporary, checksum-verified executable/model copies avoid broader Documents/Desktop access
for simulator launchd; they are removed after the probe exits. The supplied iOS static framework
requires CoreML/Foundation symbols to link; no CoreML execution
provider is selected. Failed build directories are retained and existing evidence is never overwritten.

Output is aggregate execution evidence with source/provenance/library hashes, synthetic deterministic
replay and finalization checks, and optional corpus window counts. No probabilities are converted
into public VAD accuracy without reviewed labels. Model/audio/raw scores/transcripts/clip or speaker
IDs/local paths are not committed. All physical gates remain NOT_RUN; production NOT_ENABLED.

## Duration-aware endpoint receiver

`EndpointDetector.swift` and `EndpointDetector.kt` retain their strict 320-sample legacy API and
provide a separate native-window path. The native path consumes the model's actual probability,
absolute start sample, valid sample count and final flag once. It rejects gaps, duplicates,
mixed clock APIs, invalid scores/counts and nonfinal partial windows. Padded samples never count.

`NativeVadEndpointBridge` checks a native controller/model lease when requesting input capacity
and before/after consuming a result. Revocation or closure is permanent for that receiver. It
rejects a result computed while the lease was lost, including an otherwise complete endpoint.
Default verification denies input. A native owner must still check its lease before model calls,
close/destroy the native stream on terminal results, and revalidate the controller token before
committing a returned decision. This receiver owns no native model handle and opens no capture.

Read `inputCapacity` before inference. Buffer a full 512-sample window unless the true input ends
or a hard budget requires a shorter final call. Never pad an intermediate window. Five native
high windows confirm the unchanged 2,560-sample/160 ms threshold. Silence completion requires at
least 8,000 valid low samples; full windows observe this at 8,192 samples/512 ms, not an invented
500 ms timestamp. Unknown scores reset silence/high runs. Before confirmed speech, the capacity
shrinks to 128 after 156 windows so the final call ends exactly at 80,000 samples/five seconds.
After speech, it shrinks to 256 at the 480,000-sample/30-second cap. A larger window is rejected.
Early EOF without a qualifying endpoint returns INCOMPLETE and cannot be promoted to a completed
utterance. Interruption, echo-separated speech and ASR confidence policies are unchanged.

Actual native-to-Swift simulator reproduction (existing verified cache/model only):

```sh
python3 Eilo/packages/vad-runtime/check_ios_endpoint.py --cache /local/existing/kws \
  --model /local/approved/silero_vad_v5.onnx --output /local/new-endpoint-evidence \
  --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8
```

This links the actual C ABI into a synthetic-silence Swift probe, using verified temporary copies
for execution. It verifies 157 windows/80,000 valid samples/NO_SPEECH and separately scripts lease
revocation; it is not microphone, classifier accuracy, interruption latency or Android JNI evidence.
Swift/Kotlin native owners and window delivery are now implemented below; normal capture
attachment remains gated on the outstanding trust/readiness/physical prerequisites.


## Owned native worker sprint

NativeVadStream.swift/kt own exactly one verified native stream on an inference worker. They
validate paths, lease checks before/after open and inference, native probabilities/timestamps,
input bounds and final flags. Failure, revocation and finalization terminally close the handle;
close is idempotent. Swift links the C module only under explicit DEBUG/EILO_VAD_EVALUATION.
Kotlin's ordinary default is UnavailableVadApi. NativeVadJni loads only explicitly verified,
role-matched libraries and uses monotonic opaque IDs rather than exposing C++ pointers.
Native JNI copies/clears borrowed PCM and rejects stale IDs/invalid counts. Native library
loading does not grant a trusted pack, controller generation, confidence or capture permission.

VadWindowDelivery.swift/kt lazily own that stream and one at-most-512-sample pending PCM window.
They accept sequence-addressed chunks of 1..1600 samples on the worker, preserving sample order
without retaining caller pointers. Full windows are 512; only true EOF or the hard input budget
can create a partial final window. Quiet input stops at exactly 80,000 valid samples; continuous
speech is bounded to 480,000. On a normal endpoint the last callback may be consumed only partly;
consumedSamples reports that prefix. Downstream ASR must respect this count and its own leases,
confidence and finalization policy. An invalid event consumes no further downstream data.

Capture callbacks must enqueue/copy through the existing bounded native transport; they must not
call model inference directly. The capture/turn owner must schedule close on the worker on Stop,
revocation or capture loss even if no more PCM arrives. Stop revokes the capability immediately;
cleanup must not wait under controller/capture locks. The worker checks revocation on every input,
open, native return and terminal delivery. There is no automatic capture subscription or model
readiness promotion in this sprint. Vendor internal allocator erasure remains unverified.

### Joined reproduction without downloads

First build and pin host/four-ABI JNI wrappers with existing artifacts:

```sh
python3 Eilo/packages/vad-runtime/check_jni.py --cache /local/existing/kws \
  --model /local/approved/silero_vad_v5.onnx --output /local/new-jni-build \
  --java-home /local/existing/jdk17 --ndk /local/existing/ndk/27.1.12297006
python3 Eilo/packages/vad-runtime/check_worker.py --cache /local/existing/kws \
  --model /local/approved/silero_vad_v5.onnx --output /local/new-worker-evidence \
  --java-home /local/existing/jdk17 --android-sdk /local/existing/android-sdk \
  --jni-build /local/new-jni-build --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8
```

The second command executes the whole real-model Swift worker on the existing iOS simulator
and the Kotlin worker through real macOS JVM/JNI. Its Gradle init file adds an opt-in JVM test
source only; it packages/installs no Android evaluation app. It verifies model/runtime/wrapper
hashes and source freshness before use, uses temporary local artifact copies, and refuses to
overwrite evidence. Five worker-owned streams per platform exercise 317 model calls: quiet and
irregular chunks, seven-sample EOF, revocation after actual inference and during final cleanup.
The host additionally checks raw stale JNI IDs and invalid-count revocation; those direct guard
calls are additional to the worker-scoped counters. All PCM is generated silence. No corpus
labels or quality/physical metrics are inferred.

Normal builds remain free of this evaluation native runtime/model. Host JNI execution and
four-ABI linking do not establish Android ART/phone execution. Report fields preserve those
boundaries explicitly. Existing scripted unit tests run in ordinary CI without model downloads.

## Explicit capture transport evaluation

`VadCaptureTransport` copies four <=1600-sample frames into a fixed queue, rejects >=250 ms
queue age/overflow, and coalesces scheduling onto one serial native inference worker. Stop
revokes queued results immediately and schedules worker cleanup without waiting for another
capture frame. `VadCaptureSlot` and controller-owned permits bind this to the exact capturing
turn on iOS/Android; normal app entry points do not activate it. Capture PCM may be fixed 16 or 48 kHz mono; 48 kHz is normalized on the worker as described below. Other rates and mid-stream rate changes are rejected. Optional ASR audio ownership is described below; wake/question suffix alignment, route resampling and confidence remain separately gated.

Use the same approved local cache/model/JNI build as the worker example, adding `--capture`
and a **new** output directory:

```sh
python3 check_worker.py --capture --cache "$CACHE" --model "$MODEL" \
  --output "$CAPTURE_OUTPUT" --java-home "$JAVA_RUNTIME" --android-sdk "$ANDROID_SDK" \
  --jni-build "$JNI_BUILD" --udid "$SIMULATOR_UDID"
```

This opt-in path adds only `NativeVadCaptureRuntimeTest` to the host test invocation and links
`swift_capture_probe.swift` for the already-booted iPhone18 Pro simulator. It uses synthetic
zeros and the approved native model, verifies separate worker execution and exact quiet/EOF
sample counts, and rejects Stop/cleanup revocation. `tests/capture-results.json` records five
streams/161 model calls per platform. These are transport/model checks, not physical capture,
Android ART or production readiness. Normal model-free controller/capture lifecycle tests run
in standard CI; `tests/capture-packaging-results.json` records the normal artifact exclusions.


## Optional bounded VAD-to-ASR handoff

Explicit native capture setup can provide `openAsr`, an independently verified `asrVerified`
capability (default denied), and a native-only `recognized` receiver. The worker copies only
VAD-consumed PCM prefixes into `VadAsrHandoff` (<=480000 Float32 samples / 1.92 MB), before
callback scratch is erased. Complete/capped utterances alone open ASR; no-speech and early EOF
erase the buffer without transcription. Final native text is rechecked against the capturing
permit and both capabilities after decoding/cleanup, then delivered under controller serialization.
The receiver must enqueue native work, never bridge/log text or run inference under that lock.
Unknown confidence still requires clarification through the existing recognition policy.

This version opens ASR after endpoint completion. It does not claim physical recognition latency,
route conversion, wake/question alignment, model trust readiness or production activation. Standard
Swift/JVM scripted tests cover positive exact-prefix recognition and revocation. `check_worker.py
--capture` additionally compiles the full native Swift module and executes actual approved VAD
with optional audio ownership: quiet input opens ASR zero times and clears the retained buffer.
This native regression does not test positive ASR acoustic accuracy. Current aggregate evidence:
`tests/asr-handoff-results.json` and `tests/asr-handoff-native-regression.json`.


## Fixed 48 kHz capture conversion

The explicit capture slot now supports a fixed 48000 Hz source in addition to bit-preserving
16000 Hz. The raw queue remains four <=100 ms frames; conversion and all inference stay on the
worker. StreamingRateConverter uses a pinned 193-tap Hamming FIR (7 kHz cutoff), decimates by
three, and saturates filter overshoot to [-1,1]. Its linear-phase delay is 96 source samples
(2 ms); zero startup and no EOF flush preserve exactly floor(source sample count/3) outputs.
One/two remaining raw samples are discarded at EOF. All endpoint and lastChunkConsumed metadata
uses the normalized 16 kHz clock, not raw capture indices or a latency-corrected wake boundary.

`generate_rate_filter.py --check` verifies both source coefficient tables, Float32 digest and
25-Hz-grid passband/stopband bounds; normal/optimized Python run in synthetic CI. Converter tests
also cover chunk-independent phase, streamed tones, tails, bypass identity and terminal failure.
`check_worker.py --capture` now includes 240000 raw 48 kHz zero samples through the actual approved
VAD on the simulator and host JVM/JNI: exactly 80000 normalized samples, no-speech, zero ASR opens
and cleared ownership. Latest native regression is in tests/asr-handoff-native-regression.json;
normal packaging/integration evidence is tests/route-48k-results.json.

This does not support 44.1 kHz, arbitrary rate migration or stereo downmix. iOS continues to use
its existing first input channel; Android's recorder remains configured at 16 kHz. Physical route
quality, device CPU/memory/battery, acoustic latency and clock calibration remain NOT_RUN. Normal
application model/runtime activation and production/background gates remain unchanged.
