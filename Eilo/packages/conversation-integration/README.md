# Native generic conversation integration

This internal seam joins a final bounded native ASR result, RecognitionPolicy, fixed capability/danger replies or a signed local LLM worker, NonThinkingOutput, NativeSpeechPolicy, NativeClauseQueue and an installed offline speech adapter. It has no storage, bridge-content, tool, network or permission interfaces. Configuration and all ordinary model gates default to unavailable.

Run the explicit synthetic simulator evaluator from the Eilo workspace:

```sh
python3 packages/conversation-integration/check_ios.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8
```

It requires the existing booted simulator and checksum-pinned local S03/S05/S06 model/runtime caches; it downloads/installs nothing. Wake and ASR use frozen synthetic WAVs, no microphone. A temporary signed evaluation model pack is removed after the run. The checked report describes synthetic confidence, scripted endpoint, test voice evidence and all unrun physical/egress/acoustic gates. Normal app readiness and trust configuration are untouched.

The first static joined link failed on 118 duplicated vendor symbols. The evaluator wraps the unchanged Moonshine archive in a native dynamic library with exactly the four Eilo ASR C exports and a verified TWOLEVEL namespace. Wake's static runtime remains separate; duplicate-symbol errors are never suppressed. See [Apple export guidance](https://developer.apple.com/library/archive/documentation/Performance/Conceptual/CodeFootprint/Articles/ReducingExports.html) and [library design guidance](https://developer.apple.com/library/archive/documentation/DeveloperTools/Conceptual/DynamicLibraries/100-Articles/DynamicLibraryDesignGuidelines.html). This proves simulator coexistence, not production framework embedding/signing or device execution.

Swift XCTest and Android JUnit cover final-once, low-confidence clarification, fixed danger/capability routing without inference, unavailable/default gates and stale output after Stop. Android joined native-model execution and physical airplane-mode acceptance are not yet established.
