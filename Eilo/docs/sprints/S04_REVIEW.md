# S04 — guest consent and native audio lifecycle

Gemju Sherpa verified S03 and authorized S04 on 6 October 2026, including scoped Git/GitHub commands. This is the first task checkpoint, not a completed sprint. The latest supplied AGENTS.md requires review after one small dependency-ready task.

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
