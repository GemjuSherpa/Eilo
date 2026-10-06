# S05 — VC-TURN-01 review checkpoint

Gemju Sherpa reviewed and merged S04, then explicitly authorized S05 on 7 October 2026. This checkpoint implements only VC-TURN-01 (F03, S02), whose VC-CTRL-01 dependency is approved. Branches: task/s05-vc-turn-01 → sprint/s05-turn-recognition → PR to main. Stop for review after this task; the other nine S05 tasks are not implemented here.

## Result

Android AudioRecord and iOS AVAudioEngine now retain a bounded native PCM suffix instead of immediately discarding every sample. Fixed allocation holds at most two seconds at the validated sample rate. Android uses mono PCM16 at 16 kHz (32,000 samples); iOS uses the first Float input channel at its actual validated 8–192 kHz rate without resampling. Receive timestamps expire old audio, overwritten slots are zeroed, and callback source buffers are still erased.

Stop closes/clears the ring synchronously. A per-capture ticket rejects old callbacks after Stop or a new capture. Privacy/context cleanup clears the retained samples. Android expiry runs in the existing native read loop; iOS adds a native 50 ms expiry timer only during active capture. Access purges stale samples. OS suspension can delay scheduled erasure: no hard real-time wall-clock guarantee or physical-device timing pass is claimed.

The buffer has no persistence, ASR, model, network or JavaScript consumer, and exports no PCM snapshot across the bridge. Native-only scalar inspection supports focused tests. No startup capture or readiness bypass was added. Production model readiness remains unavailable; this task does not make the app a runnable voice conversation. Wake detection, resampling/ASR handoff and recognition belong to subsequent tasks.

## Actual local evidence

- Android compileDebugKotlin, testDebugUnitTest and lintDebug: PASS. 74 JUnit tests; six new buffer/capture cases, zero failures/errors/skips.
- Swift XCTest: PASS. 66 tests; five new buffer cases, zero failures.
- iOS-platform common Swift typecheck: PASS.
- Unsigned iOS simulator Release app build: PASS. No device/signing/deployment claim.
- Focused tests: streamed wrap/chronological suffix, oversized frames without growth or caller-memory alias, two-second expiry and regressing clock, Stop/new-run stale callbacks, clear while capture remains enabled, invalid bounds/nonfinite Float samples, and actual Android capture Stop clearing both retained and reused read buffers.
- No storage or ASR adapter is reachable from this buffer. This is an inspected native API boundary; no fake hardware/model/ASR result is reported as real evidence.
- Existing build/template deprecation warnings remain. Dependency audit and S04 physical/background blockers remain unchanged.

## Reproduction and remaining checks

Run the Android JUnit task and `swift test --package-path Eilo/packages/native-test-seam`; fixtures use synthetic samples and injected monotonic clocks. Native iOS compilation validates the capture tap and expiry-timer integration. No microphone permission, real-user recording, model download or device is required for those fixtures.

Physical capture, allocation/latency measurements, timer behavior during suspension and real routing remain NOT RUN. Android/iPhone availability limitations from S04 remain. iOS background capability stays closed; screen lock still stops capture on both platforms. Approval of S04 does not establish physical feasibility or resolve its three blocked tasks.

Tracker: VC-TURN-01 implemented, partially verified, awaiting review from Gemju Sherpa. Next candidate after review: VC-TURN-02 wake detector adapter. Main merge awaits review. Existing .DS_Store and S02_REVIEW.md changes are preserved and excluded from this task.

## Review outcome — 7 October 2026

Gemju Sherpa explicitly reviewed and approved VC-TURN-01 / PR #24. All six hosted checks passed on sprint head e6307e3. Tracker review state is approved; physical verification remains partial. No main merge or subsequent S05 task execution is claimed. Next candidate: VC-TURN-02 wake detector adapter.
