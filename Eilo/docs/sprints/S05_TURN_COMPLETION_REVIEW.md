# S05 native turn recognition — review checkpoint

Gemju Sherpa authorized the remaining S05 work as one continuous run with separate task branches, task-to-sprint merges and one final PR for review. This checkpoint proposes `sprint/s05-turn-completion` against main `71092d3` (reviewed PR #40). Main merge remains with Gemju Sherpa. The local implementation and evaluation work is ready for review; S05's production and physical voice acceptance gates remain open.

## Behavior and task coverage

| Task | Implemented and tested in this sprint | Remaining acceptance work |
| --- | --- | --- |
| VC-TURN-01/02 | Existing reviewed native retention, wake adapter, verified lease and bounded worker transport; previous Android packaged decoder report remains the frozen wake baseline. | Production trust/selection/licensing/default attachment, vendor retention and physical wake calibration remain partial. |
| VC-TURN-03 | Sequence-addressed 16 kHz handoff retains at most two seconds, selects a known question suffix, rejects gaps and prevents repeated overlapping frames. Native integration tests chunk the borrowed suffix into bounded ASR frames. | A verified production capture-to-ASR caller and physical combined wake/question trials are absent. The scripted integration does not recognize real speech. |
| VC-TURN-04 | Endpoint policy confirms eight high-probability 20 ms frames; 500 ms of silence ends confirmed speech. Uncertain/overlap probabilities reset silence. No-speech timeout is five seconds; active duration is bounded to 30 seconds. | A verified native VAD probability backend and physical endpoint/pause/noise measurements are absent. Synthetic probabilities do not measure classifier accuracy. |
| VC-TURN-05 | Moonshine Small Streaming English v0.1.5 native C/C++ wrappers and Swift/Kotlin JNI adapters produce bounded partial/final text. Handles are owned, final is delivered once, Stop/revocation rejects stale text, and Eilo-owned scratch clears after borrowed calls. Real native file evaluation ran on macOS, Android ARM64 emulator and iOS ARM64 simulator. | Default runtime/model attachment remains unavailable. Vendor internal allocator erasure, complete distribution notices, microphone performance and physical ASR execution are unverified. |
| VC-TURN-06 | Empty, invalid, ambiguous, overlapping or unscored input asks “Could you say that again?” and does not reach the accepted conversational-input callback. A separately verified confidence score is required to accept text. | The evaluation backend supplies no confidence score with word timestamps disabled. Do not fabricate confidence or promote a transcript to a memory fact. Production caller wiring is pending. |
| VC-TURN-07 | Known app output and a 300 ms acoustic tail block wake/ASR activation. Stale completion and clock rollback cannot unblock a replacement turn. | Real speaker/headphone loopback and platform TTS routing are untested. This conservative gate suppresses input during known output; it is not full-duplex echo cancellation. |
| VC-TURN-08 | Eight consecutive high-probability frames with independently verified user-speech evidence cancel old reply work before minting a replacement token. Noise, short bursts and self-output markers do not cancel. Stop/revocation during cancellation cannot revive a run or release an old queued clause. | The independent echo-separated speech route is not implemented in the normal app. The scripted 160 ms timestamp is a sample-clock assertion, not physical interruption p95 or audible tail latency. |
| VC-TURN-09 | A reproducible aggregate report distinguishes frozen synthetic wake scores from physical results; a physical trial protocol is documented. | Frozen quiet route trials and an eight-hour labelled ambient dataset/capture attachment are unavailable. Physical detection/false-activation results remain NOT RUN. |
| VC-TURN-10 | Frozen word normalization and Levenshtein reporting expose substitutions/deletions/insertions by sample and slice, including failures. | The six-case, single US-English synthetic voice set supplies no accent diversity or physical microphone quality evidence. |

The normal app still reports missing model readiness. It does not activate microphone capture, conversational inference or full-duplex interruption from these evaluation results. S06 local reply inference and S07 offline TTS remain separate work. No cloud inference, personal audio collection, service provisioning or paid service was added.

## Measured recognition results

- The existing real Android native wake evaluation reports 11/11 intended positives and zero false activations across 15 scored nonwake entries. Two diagnostics are excluded; the 28-entry set uses 24 unique WAV files. These are synthetic file results, not a physical false-activation rate per hour.
- Actual macOS, Android and iOS simulator ASR evaluation each produced six word errors across 40 reference words: **15% WER**. The name case has two errors in five words; the number case has four errors in 11 words. Other cases match the frozen normalization. Names and number formatting were not repaired after evaluation.
- System-generated fixture audio, model files and vendor binaries remain in ignored local caches. Published reports contain generic synthetic references only. No microphone recording or real conversation was collected.

See [wake summary](../../packages/wake-runtime/tests/wake-trial-summary.json), [ASR quality results](../../packages/asr-runtime/tests/quality-results.json), [native ASR reproduction](../../packages/asr-runtime/README.md) and [physical trial protocol](S05_PHYSICAL_TRIALS.md).

## Final checks — 12 October 2026

| Check | Result and boundary |
| --- | --- |
| Android Kotlin compiler, JUnit and lint | PASS: 143 tests, zero failures/errors/skips. |
| Swift compiler/XCTest seam | PASS: 113 tests, zero failures. Tests execute on macOS, not on the physical iPhone. |
| Native integration | PASS on both test seams: wake suffix → bounded ASR feed → endpoint → unscored-text clarification; duplicate frames delivered once; Stop/new-run during final rejects old text. Backend text and VAD are scripted. |
| Workspace ESLint and TypeScript | PASS for configured mobile/contracts workspaces. |
| Workspace JavaScript tests | PASS: nine mobile tests and 33 contract tests. |
| ASR/wake report validation | PASS: two ASR quality tests and two wake summary tests. |
| Normal Android Debug/Release packaging | PASS. Evaluation vendor libraries, models and instrumentation are excluded from normal APKs. |
| Same iPhone 18 Pro / iOS 27.0 simulator | Debug build PASS; three fresh ten-second launches PASS before the interruption commit. The final integration change adds test sources and documentation only. |
| Physical iPhone 17 Pro Max / iOS 26.6.1 | Signed Debug and Release builds/install PASS. Developer trust confirmed by successful Debug launch. Release contains `main.jsbundle`; three fresh processes each survived ten seconds. Gemju Sherpa confirmed Home renders normally. |
| Physical voice/route/latency/privacy endurance | NOT RUN. Startup does not establish microphone recognition, ASR quality, interruption p95, background feasibility, retention or an offline conversation. Networking was not disabled on the phone. |

The first Release launch attempt was denied because the phone was locked. After Gemju Sherpa unlocked it, all three fresh Release launch checks passed. No device unlock, microphone consent, readiness or security gate was bypassed. Personal signing configuration stays local and is excluded from the PR.

## Reproduce local checks

From the repository root, use the existing installed toolchains:

```sh
swift test --package-path Eilo/packages/native-test-seam
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
ANDROID_HOME=/Users/gemju/Library/Android/sdk \
Eilo/apps/mobile/android/gradlew -p Eilo/apps/mobile/android \
  :app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug \
  :app:assembleDebug :app:assembleRelease --offline --max-workers=2
python3 -m unittest discover -s Eilo/packages/asr-runtime -p 'test_*.py'
python3 -m unittest discover -s Eilo/packages/wake-runtime -p 'test_trial_summary.py'
```

From `Eilo`, run `npm run lint`, `npm run typecheck` and `npm test`. The native ASR README describes the separately authorized synthetic runtime evaluations and exact asset checksums; evaluation assets are not required for ordinary unit checks.

For simulator startup, build Debug from `apps/mobile/ios/Eilo.xcworkspace`, install on the same booted simulator and run `scripts/verify-ios-launch.py --udid <simulator-udid> --dwell 10`. For the physical startup check, select the connected iPhone and local signing team, build/install Release from the workspace, then perform three fresh `devicectl device process launch --terminate-existing` invocations while the phone is unlocked. After each ten-second dwell, query only Eilo with `devicectl device info processes --search Eilo`; verify a distinct app process remains running. The Release bundle removes Metro from startup, but this procedure does not test network-disabled conversation.

## Source control and review limits

Separate task branches cover VC-TURN-03 through 10; each tested task is committed, pushed and merged into the sprint branch. `task/s05-turn-integration-review` adds the final cross-component tests, physical startup evidence and this review record. Main remains untouched. Final staged diff and secret scans precede this task commit; the final PR requests review rather than sprint acceptance or release approval.

The unrelated S02 review edit, Info.plist ordering and local Xcode formatting/signing changes are preserved and excluded. Root instruction documents and the knowledge-transfer JSON/CSV/handoff remain ignored; their local trackers record partial verification and pending review. No task is promoted to approved by this PR. Next acceptance work is verified VAD/production turn attachment, echo-separated user speech, frozen physical wake/ASR/route trials and the full pipeline/device performance evidence described above.
