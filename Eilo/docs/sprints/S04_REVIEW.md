# S04 — guest consent and native audio lifecycle

Gemju Sherpa verified S03 and authorized S04 on 6 October 2026, including scoped Git/GitHub commands. Gemju Sherpa subsequently authorized continuing the remaining S04 tasks before the sprint review. Task results and unrun physical checks are recorded below.

## VC-AUDIO-01 — Android foreground capture

Requirements F01 and F17; dependencies VC-SET-04 and VC-CTRL-01 are approved with recorded physical-integration limitations. Branch: task/s04-vc-audio-01; integration branch: sprint/s04-guest-audio.

Before: Android had a fail-closed Noop capture effect. After: the application owns an AudioRecord adapter and a native worker independently of React Native. Construction never captures. Explicit controller Start plus readiness, granted microphone permission, visible activity and unlocked device are required. Opening occurs asynchronously; no listening/standby state or generation is issued before confirmed recording. Stop and activity exit cancel pending opens, invalidate callbacks and release a live recorder. Permission/model changes still fail closed.

PCM is reused only in a bounded native buffer, erased after each read, and discarded. No raw audio, transcription, file sink, network client or JavaScript audio bridge was added. No background capture, notification, consent screen, iOS audio or TTS was implemented in this task. Production model trust/readiness stays unavailable; the existing UI has no Start command until VC-SET-06. This is native integration groundwork, not a runnable conversation demo.

## Verification

- Kotlin compileDebugKotlin: PASS using installed JDK 17 and Android SDK.
- Android testDebugUnitTest: PASS, 54 JUnit tests, zero failures. Nine new tests cover pending Start without a generation, duplicate Start, delayed completion after Stop, revoked permission, stale failure versus a new run, hidden/exit-during-open capture, cancellation during open, native read failure, buffer erasure and construction failure. Existing controller/privacy/model tests remain green.
- Initial debug/release packaging passed. The initial Android lint run found a missing explicit device-boundary permission check (fixed) and 46 pre-existing API-26 file API usages against minSdk 24. The build minimum was corrected to 26, the smallest required API level. Android 15/8 GB remains a provisional physical evaluation baseline, not certified support. Final lint/build results follow below.
- Physical Android Start/Stop, mic indicator, JS suspension, hardware capture/permission revocation and foreground lifecycle: NOT RUN. Gemju Sherpa previously reported no Android phone. The synthetic device adapter tests cannot establish hardware behavior.
- Native audio reads are nonblocking but short platform Start/Stop/release calls can still take device-dependent time. No interruption-latency target is claimed. OS silencing/contention and focus events belong to VC-AUDIO-04.

## Physical reproduction when the dependency-ready test harness is available

Use synthetic speech only on a declared Android phone. Verify no install/relaunch capture; Start with denial and grant; inspect the mic indicator; suspend/detach JS while foreground; Stop natively; exit while a device open is pending; revoke permission; verify samples do not appear in logs/files/bridge traffic. Record model, OS, timings and actual native states. Do not bypass production readiness or silently inject a ready-model adapter to make this pass.

## Review checkpoint

VC-AUDIO-01 is implemented with partial verification and awaits Gemju Sherpa review. S04's other 15 tasks remain planned. No main merge or release assurance is claimed for this partial sprint. Next dependency-ready task is VC-AUDIO-05, after review.

## Final local checks — 6 October 2026

PASS: `:app:compileDebugKotlin :app:testDebugUnitTest :app:assembleDebug :app:assembleRelease :app:lintDebug` on JDK 17/installed Android SDK (54 JUnit tests, zero failures). Android lint now has zero errors; existing dependency/template warnings remain. PASS: npm workspace lint, typecheck and tests (33 contract tests plus one mobile UI test). No iOS source changed; its hosted regression build remains part of the existing CI workflow. No dependencies were installed and no infrastructure was provisioned.

Official platform reference: [Android AudioRecord](https://developer.android.com/reference/android/media/AudioRecord), including nonblocking reads, recording-state checks and resource release. This reference is implementation guidance, not evidence of a hardware pass.

### VC-AUDIO-05

iOS AVAudioEngine/session capture is process-owned and native-only; asynchronous Start/Stop, stale completion, permission revocation and setup-race fixtures pass. Swift 48 tests and iOS-platform typecheck pass. Hardware Start/Stop and JS-detached capture are NOT RUN.

### VC-AUDIO-02

Unexported, non-sticky microphone foreground service owns a generic ongoing notification. Its immutable Stop pending intent calls native Stop without opening UI; teardown cancels capture. Kotlin, 55 JUnit tests and Android lint pass. Actual notification tap/microphone release is NOT RUN on physical Android.

### VC-AUDIO-04

Native OS focus loss/duck, native capture-loop permission checks, client silencing and capture errors stop/release and invalidate work; focus gain never restarts. Independent event matrix rejects stale speech. Kotlin, 56 JUnit tests and Android lint pass. Physical calls/revocation/contention not run.

### VC-AUDIO-07

AVAudioSession interruption-began and media/engine reset observers stop native capture and volatile work without resuming on interruption end. Permission availability uses the existing version-checked adapter. Swift 49 tests, platform typecheck and unsigned iOS Release build pass. Physical call/revocation checks NOT RUN.

### VC-AUDIO-08

Android private-output device removal and iOS old-device-unavailable events stop/invalidate work. Native speech release stays blocked across fresh Start until explicit unlocked speaker confirmation; reconnection never confirms. Kotlin 57 tests/lint and Swift 50 tests/typecheck pass. Real headphone/Bluetooth routing and spoken playback remain NOT RUN.

### VC-SET-01

Accessible English guest disclosure explains AI/adult audience, local processing, unsaved audio, optional encrypted text, unfinished history capability, local-loss limits and separate microphone/background choice. Guest UI reaches setup without identity fields/requests. Workspace lint/types and 34 JS/UI tests pass; physical screen-reader/large-text checks pending.

## S04 dependency and build decisions

React Navigation native 7.5.0, native-stack/bottom-tabs 7.20.0 and react-native-screens 4.28.0 are pinned in the npm lockfile (MIT). Official registry peer requirements accept existing React 19.2.3, RN 0.87.1 and safe-area 5.10.1; actual native builds are checked below. No additional global JS state system was introduced. The native controller remains authoritative.

RN 0.87.1 Codegen uses shell `find` with an unquoted project path when app specs are present. `scripts/patch-codegen-paths.mjs` replaces these calls with `execFileSync` argument arrays, verifies the exact RN version and source anchors, and runs on npm postinstall. It preserves the vendor license and fails for review if upstream changes. CocoaPods regeneration passes at the existing path with spaces.

The current npm audit reports 53 dependency advisories (48 high, five moderate, zero critical); none names the four selected navigation packages. This is not a clean security audit. Full dependency remediation/release assessment remains outstanding; no force-upgrade or security bypass was applied.

### VC-SET-06

Generated TurboModule exposes allowlisted commands and strictly validated metadata only. Home requests native Start/Stop, offers Stop during pending/unknown state, and explicitly confirms speaker output. Monotonic native revisions reject old snapshots; UI detach/reconnect tests read changed native state without owning capture. Workspace lint/typecheck, 39 JS/UI tests, Kotlin 57 tests/lint, Swift 50 tests and unsigned iOS Release build pass. Physical control/VoiceOver/TalkBack checks pending.

### VC-SET-02

Versioned native consent metadata requires an unselected-to-explicit history/private choice; microphone permission cannot set it. Native onboarding completion is persisted only after a choice. Failed/unknown-version persistence fails closed. History request never enables unavailable encrypted storage; Start requires a deliberate usable/private choice. Native metadata stays local, iOS file is complete-protected and backup-excluded. Kotlin 60 tests/lint, Swift 53 tests/typecheck, 40 JS/UI tests and unsigned iOS Release build pass. Physical storage/backup/accessibility checks pending.
