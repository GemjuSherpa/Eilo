# Native generic conversation integration

This internal seam joins a final bounded native ASR result, RecognitionPolicy, fixed capability/danger replies or a signed local LLM worker, NonThinkingOutput, NativeSpeechPolicy, NativeClauseQueue and an installed offline speech adapter. It has no storage, bridge-content, tool, network or permission interfaces. Configuration and all ordinary model gates default to unavailable.

Run the explicit synthetic simulator evaluator from the Eilo workspace:

```sh
python3 packages/conversation-integration/check_ios.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8
```

It requires the existing booted simulator and checksum-pinned local S03/S05/S06 model/runtime caches; it downloads/installs nothing. Wake and ASR use frozen synthetic WAVs, no microphone. A temporary signed evaluation model pack is removed after the run. The checked report describes synthetic confidence, scripted endpoint, test voice evidence and all unrun physical/egress/acoustic gates. Normal app readiness and trust configuration are untouched.

The first static joined link failed on 118 duplicated vendor symbols. The evaluator wraps the unchanged Moonshine archive in a native dynamic library with exactly the four Eilo ASR C exports and a verified TWOLEVEL namespace. Wake's static runtime remains separate; duplicate-symbol errors are never suppressed. See [Apple export guidance](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/CodeFootprint/Articles/ReducingExports.html) and [library design guidance](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryDesignGuidelines.html). This proves simulator coexistence, not production framework embedding/signing or device execution.

The current evaluator executes three completed generated spoken turns, including a replacement of one SDK-started scripted generic reply. Interruption VAD/separation evidence is synthetic. It exercises follow-up with one initial wake, a scripted suffix boundary and completed volatile context; it verifies explicit end closes the session. Context is capped at four pairs/8192 bytes and clears on end/idle/Stop/privacy.

Swift XCTest and Android JUnit cover final-once, low-confidence clarification, fixed danger/capability routing without inference, unavailable/default gates and stale output after Stop. Android joined native-model execution and physical airplane-mode acceptance are not yet established.

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
speech executable excludes the unrelated protected-key provider; normal application builds
still compile that provider. One temporary ten-artifact ES256 lab pack holds speech and LLM
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
