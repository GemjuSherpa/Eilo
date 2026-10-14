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
weakened. The normal app does not import/link/activate this package. No microphone, network,
downloader, runtime installation or application launch occurs in these checks.

**Timing boundary:** native probabilities cover 512 samples (32 ms). Existing EndpointDetector
expects 320-sample (20 ms) probabilities. Do not duplicate a probability into multiple 20 ms
frames or use segment detection as a probability. A duration-aware, separately reviewed bridge
and Swift/Kotlin lifetime/lease bindings are still needed before capture integration. This task
does not change endpoint thresholds, silence/no-speech limits or interruption policy.

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
