# Native generic conversation integration

This internal seam joins a final bounded native ASR result, RecognitionPolicy, fixed capability/danger replies or a signed local LLM worker, NonThinkingOutput, NativeSpeechPolicy, NativeClauseQueue and an installed offline speech adapter. It has no storage, bridge-content, tool, network or permission interfaces. Configuration and all ordinary model gates default to unavailable.

Run the explicit synthetic simulator evaluator from the Eilo workspace:

```sh
python3 packages/conversation-integration/check_ios.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8
```

It requires the existing booted simulator and checksum-pinned local S03/S05/S06 model/runtime caches; it downloads/installs nothing. Wake and ASR use frozen synthetic WAVs, no microphone. A temporary signed evaluation model pack is removed after the run. The checked report describes synthetic confidence, scripted endpoint, test voice evidence and all unrun physical/egress/acoustic gates. Normal app readiness and trust configuration are untouched.

The first static joined link failed on 118 duplicated vendor symbols. The evaluator wraps the unchanged Moonshine archive in a native dynamic library with exactly the four Eilo ASR C exports and a verified TWOLEVEL namespace. Wake's static runtime remains separate; duplicate-symbol errors are never suppressed. See [Apple export guidance](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/CodeFootprint/Articles/ReducingExports.html) and [library design guidance](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryDesignGuidelines.html). This proves simulator coexistence, not production framework embedding/signing or device execution.

The current evaluator executes three completed generated spoken turns, including a replacement of one SDK-started scripted generic reply. Interruption VAD/separation evidence is synthetic. It exercises follow-up with one initial wake, a scripted suffix boundary and completed volatile context; it verifies explicit end closes the session. Context is capped at four pairs/8192 bytes and clears on end/idle/Stop/privacy.

Swift XCTest and Android JUnit cover final-once, low-confidence clarification, fixed danger/capability routing without inference, unavailable/default gates and stale output after Stop. The original evaluator establishes iOS simulator execution. Android ART execution is recorded separately below; physical airplane-mode acceptance remains open.

## Signed VAD/ASR capture to generated spoken follow-up

`check_capture_ios.py` replaces scripted endpointing/direct ASR in this evaluation with the real
signed SpeechCaptureInstaller, Silero endpointing, bounded retained PCM and Moonshine decoding.
It runs two generated spoken turns (16 kHz, then a sample-repeated 48 kHz follow-up) and a quiet
capture with no reply. The exact synthetic question is checksum-pinned; only its transcript
hash is reported. The follow-up uses the completed two-message context and completes with four.
A second submission of each final is rejected. Model inference stays on separate native workers;
the main thread submits each accepted final to GenericSpokenTurn only after capture cleanup.

Invoke from the workspace with existing approved caches and a new output directory:

```sh
python3 packages/conversation-integration/check_capture_ios.py \
  --asr-cache "$ASR_CACHE" --vad-cache "$VAD_CACHE" --vad-model "$VAD_MODEL" \
  --llm-cache "$LLM_CACHE" --llm-model "$LLM_MODEL" --output "$NEW_OUTPUT" --udid "$SIMULATOR_UDID"
```

The runner verifies runtime/model inputs, rebuilds the CPU LLM from the pinned source with the
recorded CPU-only configuration, rejects network symbol dependencies, and retains build hashes.
It uses the existing four-export ASR wrapper to isolate bundled ONNX symbols. Its strict Swift
speech executable now includes every native Swift source, including the protected-key provider.
The provider uses the current authentication-context prompt API; it is not invoked by this test. One temporary ten-artifact ES256 lab pack holds speech and LLM
weights. It is removed before the aggregate report is emitted. No model/runtime binary is committed.

Confidence is synthetic 0.95; exact voice/OS offline evidence is synthetic. SDK completion does
not establish first audible timing, intelligibility or hearing. The 48 kHz signal is repeated
16 kHz input, not hardware capture. No wake boundary, microphone, physical route, Android ART,
production model trust or ordinary app caller is established. Native Swift and Android unit tests
cover final-to-reply Stop/privacy rejection, unknown-confidence clarification and duplicate denial;
the Android tests use scripted native APIs and a scripted clause sink.

`tests/ios-capture-results.json` and `tests/capture-evidence.json` pin aggregate results and the
evaluated input sources. `check_capture_evidence.py` and `test_capture*.py` run without SDKs/models
in synthetic CI, in normal and optimized Python. They validate evidence, not native re-execution.

## Android ART capture/reply and existing offline SDK

The Android runner uses only verified existing caches, API 35 ARM64, NDK
27.1.12297006, and an explicitly selected existing emulator. It runs the real
signed VAD/ASR installer, signed Qwen3-1.7B local CPU generation, output screening,
speech policy and native clause queue. No microphone or ordinary app caller is
activated. The evaluation APK removes both Internet and microphone permissions;
its normal replacement APK is inspected and reinstalled in a `finally` block.

```sh
python3 packages/conversation-integration/check_capture_android.py \
  --serial "$EMULATOR_SERIAL" --asr-cache "$ASR_CACHE" --vad-cache "$VAD_CACHE" \
  --vad-model "$VAD_MODEL" --ort-headers "$ORT_HEADERS" \
  --llm-cache "$LLM_CACHE" --llm-model "$LLM_MODEL" --cmake "$CMAKE" \
  --ndk "$ANDROID_NDK" --java-home "$JAVA_HOME" --android-sdk "$ANDROID_HOME" \
  --output "$NEW_OUTPUT" --speech-sdk
```

`--speech-sdk` selects a currently installed offline English voice through the
real Android adapter. Output gain is zero; SDK completion is not audible-output,
intelligibility or acoustic acceptance. Omitting that flag uses an asynchronous
synthetic clause sink. Each mode has its own actual three-case report: initial
16 kHz reply, sample-repeated 48 kHz follow-up with completed volatile context,
and quiet input that starts no reply. The two completed replies each produce two
clauses in the recorded runs. Duplicate final submission is denied.

For the independent model-free voice/SDK prerequisite check:

```sh
python3 packages/conversation-integration/check_speech_android.py \
  --serial "$EMULATOR_SERIAL" --java-home "$JAVA_HOME" \
  --android-sdk "$ANDROID_HOME" --output "$NEW_OUTPUT"
```

That check reports either fixed-clause SDK start/finish callbacks or an explicit
missing-offline-voice blocker. It never requests a package or voice download.
Neither app permission removal nor a voice's offline flag isolates the speech
engine's separate process; network acceptance remains NOT_RUN.

`tests/android-capture-*.json`, `tests/android-sdk-capture-*.json`, and
`tests/android-speech-*.json` bind redacted aggregates to evaluated sources.
The Android evidence checkers and tests run offline in CI under normal and
optimized Python; they do not rerun native models or SDKs. The original ONNX
model, converter, options and runtime are fixed, but local ORT serialization may
vary in digest/size; each signed evaluation pack records its own derived bytes.
Controller readiness, permission state and ASR confidence are synthetic. Physical
microphone/speaker, wake alignment, echo separation, latency, network and release
acceptance remain open. Production trust and ordinary app activation are unchanged.


### Joined iOS framework simulator execution

`check_framework_capture.py` uses the reviewed `CEiloAsr.xcframework` simulator slice
with real VAD, signed evaluator model installation, loaded Qwen CPU inference and
SDK speech completion. The client is moved before execution, with the original
client absent and only the embedded framework loader path available. Speech volume
is zero in an evaluator-only sink; production speech behavior is unchanged.

The three file-fed cases cover 16 kHz speech, a 48 kHz follow-up and silence. The
first two must complete replies and retain two/four volatile context messages;
silence must not start inference. Synthetic confidence 0.95, lab trust and exact
voice/OS evidence remain explicit. This does not qualify confidence, offline voice
availability, ordinary-app embedding, signing, physical behavior or release.

Run `python3 framework_capture_report.py` and
`python3 -m unittest discover -p test_capture_framework.py -v` to audit the committed
aggregate without native caches; both also run with Python optimization in CI.
The native runner requires `--asr-cache`, `--vad-cache`, `--vad-model`, `--llm-cache`,
`--llm-model`, `--framework`, a fresh `--output` and a booted `--udid`. It downloads
nothing and uses no microphone. Native models and logs stay in ignored local
storage. CI uploads only the redacted JSON/HTML summary for seven days.


### Frozen paired iOS noise replay

`framework_noise.py` reuses the exact 18 approved MUSAN/synthetic control prefixes
from the earlier direct-ASR diagnostic. A committed protocol appends 32,000 zeros,
pads short inputs to 80,000 samples and caps at 480,000, all at 16 kHz. Each input
runs through direct ASR and the signed VAD→ASR path using the same reviewed iOS
framework/models; endpoint consumption differs. A known question exercises both
paths as a positive runtime control. No microphone, wake, LLM or speech SDK runs.

Actual observation: both paths returned empty final text for all 18 negative
controls. VAD kept ASR closed for 16, while two weakly labelled MUSAN clips reached
ASR and returned empty text. All six synthetic no-speech controls ended with
noSpeech and no ASR open. The positive question produced nonempty text in both
paths. This measures nonempty text and model opens, not word accuracy, calibrated
confidence or system false activation. MUSAN category labels do not establish
speech absence. These padded iOS inputs and runtime differ from the earlier raw
Android score diagnostic, so the reports do not estimate an improvement over it.

The protocol/runner/probe were committed before execution. Source, model, original
control and transformed input hashes are checked, and all native handles close.
Unavailable direct/joined results remain explicit unknowns in the exporter. CI
runs report mutation tests and source/protocol checks without native caches and
uploads only JSON/HTML summaries for seven days. No raw audio or text is committed.

Reproduce aggregate validation with `python3 framework_noise_report.py` and
`python3 -m unittest discover -p test_capture_noise.py -v`, also under `python3 -O`.
Native execution requires explicit approved cache/manifest/model/framework paths,
a booted simulator UUID, fresh output and `--protocol-commit` containing the exact
runner/probe/protocol bytes. It refuses overwrite and has no download fallback.
Physical remains OPEN/NOT_RUN, confidence NOT_EVALUATED, calibration
NOT_ESTABLISHED, threshold NOT_GRANTED, full-system false activation NOT_MEASURED,
S08/release HOLD and persistent memory DISABLED.
