# Isolated native ASR probability prototype

This file-fed Android executable demonstrates that the pinned streaming model exposes nonconstant token probabilities without an attention model or production runtime replacement. It links a minimal source subset to the already cached ORT1.23.2. No microphone, speech playback, app install, network observer or physical device is used. It never changes the app's unknown-confidence policy.

All six **synthetic system-voice** fixtures passed actual ARM64/API35 emulator execution. Each token's probability is a numerically stable softmax over the full, unmodified decoder logit row. EOS is excluded; BOS is input only. Arithmetic mean, geometric mean, minimum and maximum are diagnostics, not calibrated utterance confidence or word confidence. The upstream timestamp confidence constant is unused.

The harness compares greedy `decode_step` with teacher-forced batched `decode_tokens` over the accepted draft. It requires the predicted tokens to match and deliberately corrupts the draft's first token to verify rejection. The greedy and batched probabilities are reported separately: the maximum observed individual probability difference is about **0.146**, so their scores must not be treated as interchangeable. The cause has not been established. This does not instrument the SDK's `decode_full` speculative acceptance, cache rewind or context-bias behavior; those integration tasks remain open. No biased logits are scored.

Input is bounded to30 seconds/16kHz mono finite float PCM in[-1,1]. Decode is bounded to128 tokens and must reach EOS. The harness refuses empty encoder memory before invoking the SDK's synthetic empty-memory EOS fallback. Empty, misaligned, NaN and out-of-range files are tested to emit no score. Unknown/invalid signals fail closed. Reports contain aggregates and hashes, with no audio, transcripts, token IDs or per-token score arrays.

## Reproduce from existing caches only

Review `SOURCE_REVIEW.md` and `source-manifest.json`. The entire source inventory must match its immutable Git blob hashes; source retrieval is a separate, explicitly authorized operation. This command downloads nothing and expects the existing API35 ARM64 emulator on `emulator-5554` to be running. It refuses an existing remote probe directory, cleans its own temporary directory in `finally`, preserves the normal installed app, and refuses to overwrite evidence.

From the Eilo workspace, supply absolute paths to the existing caches/tools:

```sh
python3 packages/asr-confidence-probe/check_android.py \
  --source "$SOURCE_CACHE" --cache "$ASR_CACHE" --build "$LOCAL_BUILD" \
  --ndk "$ANDROID_NDK" --android-sdk "$ANDROID_SDK" --cmake "$CMAKE" \
  --serial emulator-5554 --output "$NEW_REPORT"
python3 -m unittest discover -s packages/asr-confidence-probe -p 'test_*.py' -v
python3 -O -m unittest discover -s packages/asr-confidence-probe -p 'test_*.py' -v
python3 packages/asr-confidence-probe/report.py
```

`android-results.json` binds the actual binary, model/fixture provenance, source inventory, harness and math code. CI checks those pins and hostile report mutations plus native softmax numeric edge cases without source/model downloads. Binary hashes record local build provenance; CI does not independently reproduce native inference. Build outputs remain ignored and must stay within the approved5GiB budget.

Next work is investigating the path-dependent probabilities, instrumenting actual speculative/greedy SDK selection with aligned pre-bias scores, then evaluating correctness/calibration on a held-out licensed corpus. Synthetic native scores do not establish that calibration. Any production integration requires fresh relevant native evidence. All physical, acoustic, privacy/network and release gates remain unchanged; S08/release HOLD and persistent memory disabled.
