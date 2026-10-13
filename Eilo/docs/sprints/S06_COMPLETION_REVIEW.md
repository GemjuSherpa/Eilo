# S06 implementation review

The S06 sprint branch contains separate tested task branches for the native Swift model worker, offline voice readiness/adapters, bounded clause playback/progress, non-thinking prompt/output handling, tokenizer budgets, untrusted memory and bounded continuation. It also contains frozen physical trial protocols with explicitly unrun result records. **S06 is not fully accepted: physical voice quality and CPU model comparison remain blocked.** Main has not been merged by this workflow.

| Stable task | Current result |
| --- | --- |
| VC-LLM-01 | Swift controller-owned worker implemented/tested; parent remains partial for production caller/trust/licensing and physical performance |
| VC-VOICE-01 | Installed English offline voice selection/readiness contract tested; unknown capability denied without exact evidence |
| VC-VOICE-02 | Android exact offline SDK voice adapter and emulator completion tested |
| VC-VOICE-03 | iOS exact voice/OS evidence adapter and simulator completion tested; injected evaluation evidence is synthetic |
| VC-VOICE-04 | Controller-owned natural-clause assembly/queue, bounds, ordering, cancellation and generation/playback state tested |
| VC-VOICE-05 | Bounded default-denied native playback metadata tested; no heard claim or history writes |
| VC-LLM-02 | Official pinned Qwen non-thinking template goldens and split UTF-8/markup output guard tested; actual simulator CPU completions pass |
| VC-LLM-03 | Actual loaded-vocabulary 4096 context / 512 recall / 256 output budgets and trim policy tested on simulator/emulator |
| VC-LLM-04 | Dedicated quoted untrusted recall section, structural injection boundary and default exclusion tested |
| VC-LLM-05 | One policy per generation, four approved chunks / 1024 total tokens, context bounds and Stop revocation tested |
| VC-VOICE-06 | Protocol/12 utterances/evidence validator prepared; physical timing/availability/intelligibility NOT RUN |
| VC-LLM-06 | Protocol/six prompts/rubrics/evidence validator prepared; physical 1.7B-vs0.6B comparison NOT RUN |

Review records for each task live beside this document. The local stable tracker retains all 175 IDs; tests do not establish Gemju Sherpa approval. Physical records remain NOT_RUN with null measurements, not placeholder zeros. The offline iPhone's friendly device name does not establish its hardware model; physical Android is unavailable. The 0.6B artifact, exact comparison adapter and physical measurement target still need preparation. Production pack trust/licensing, vendor allocator retention, physical audio-stop/network/latency evidence and the ordinary joined speech turn remain open; S07 owns app turn assembly/pre-speech policy and S08 owns protected retrieval/history authorization.

Validation on 13 October 2026: **242 Android tests and192 Swift tests pass**, including queue/Stop/privacy/continuation regressions. A final Android cancellation-hook safeguard ensures a thrown signal cannot prevent Stop cleanup. Android lint, normal Debug build and Release Kotlin compile pass. Strict Swift source compilation and workspace lint/typecheck pass; 9 mobile and 33 contract tests pass. 31 scripted C ABI lifecycle/count scenarios pass under ASan/UBSan; provenance/download/evidence tests pass. The official pinned Jinja template matches three native goldens.

Actual Qwen3-1.7B CPU evaluation passes through signed evaluation packs/controllers on the iOS simulator and API35 ARM64 Android emulator, with lifecycle/revocation/default gates. Actual loaded-vocabulary context/recall trimming and generation pass with the final memory section. Both ARM64 iOS SDK links and all four Android CPU/JNI ABI links pass. Android inference socket probes are denied and its normal APK is restored without evaluator assets/library/source; iOS OS-wide network isolation remains unverified. Speech SDK probes complete on simulator/emulator; iOS offline voice evidence is explicitly synthetic. No microphone or physical inference is claimed.

Every app code task was built/installed on the same iPhone 18 Pro simulator and passed three fresh ten-second launches before its commit. Task commits were pushed and merged into the S06 sprint branch. Only scoped Xcode source references and the AVFoundation bridge import were committed; existing personal signing/plist/S02 changes are preserved and excluded. No paid service, tool installation, deployment or automatic main merge was performed. Staged/full sprint-history secret scans precede publication.

Reproduce from the repository root using existing installed dependencies:

```sh
cd Eilo
npm run lint
npm run typecheck
npm test
cd packages/native-test-seam
swift build -Xswiftc -warnings-as-errors
swift test
```

For Android, run the existing Gradle wrapper from `Eilo/apps/mobile/android` with JDK17/installed SDK: `./gradlew --offline --max-workers=2 :app:testDebugUnitTest :app:lintDebug :app:assembleDebug :app:compileReleaseKotlin`. Run Python evidence tests with `python3 -m unittest discover -s Eilo/packages/llm-runtime -p 'test_*.py'` and the corresponding offline-speech directory. `check_template.py` requires the existing model-build environment/Jinja and pinned tokenizer configuration.

Native runtime checks require the ignored, hash-verified llama.cpp source archive and pinned 1.7B GGUF described in `packages/llm-runtime/README.md`; they download/install nothing. Use `check_host.py --contract-only`, `check_ios.py --udid <the-existing-booted-simulator>`, and `check_android.py` with the installed pinned NDK/JDK/SDK plus existing emulator serial. The Android evaluator restores the normal app. These are explicit evaluation capabilities and do not enable the ordinary app's model-ready gate. Read the two physical protocols before collecting phone measurements; their validators validate shape, not truth or acceptance.

Gemju Sherpa: review the implementation and disclosed remaining gates before merging the final S06 PR. The physical trial tasks must remain open after that merge until actual measurements and review are complete.

Final review safeguard: each active clause has a 60-second watchdog. A missing SDK completion fails closed, schedules stop, clears waiting text and rejects late callbacks; the timeout is not an acoustic-stop timing claim. A focused test on each platform verifies this stall case.

Speech ticket publication is atomic with the controller: the queue receiver initializes before cancellation can observe it, and a Stop during publication rejects attachment. Deterministic regressions cover this constructor/Stop race on both platforms.
