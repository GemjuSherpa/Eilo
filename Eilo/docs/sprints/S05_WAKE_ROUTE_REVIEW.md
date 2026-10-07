# S05 — Wake stream sample-rate boundary

VC-TURN-02 / F03 / A02 follow-up. Gemju Sherpa reviewed and merged PR #28; verified main is 2c96713. Start sprint/s05-wake-mobile and task/s05-vc-turn-02-route-rate from that main. This is a prerequisite boundary fix for native mobile wake integration, not completion of vendor bindings or ASR.

## Before and after

The C++ wake wrapper already rejects a sample-rate change within one stream. Kotlin and Swift adapters validated each individual rate but allowed alternating rates through one backend. An audio route change could therefore feed incompatible timing into a streaming recognizer and leave a pending wake activation valid, depending on the installed backend.

Both adapters now bind the stream to the first valid frame rate. A subsequent changed rate closes the backend before accepting that frame, erases scratch storage, revokes its activation lease and discards the rate binding. Reopening requires explicit begin; a fresh generation can use a different valid rate. Stale frames with an old generation cannot close or alter the new stream. The adapters still default to unavailable until independently verified assets and a backend are supplied.

## Checks

- Swift native package: compiler and 78 XCTest tests PASS. New regression covers changed-rate rejection before backend input, prior activation revocation, scratch erasure, no implicit reopening, fresh-rate restart and stale-generation isolation.
- Negative control in an isolated temporary Swift package with only the rate guard removed: the new regression fails with five assertions. Workspace source was not reverted or changed for the control.
- Android `:app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug`: PASS; 86 tests, zero failures. Equivalent route/generation regression included.
- Xcode unsigned Debug build targeting the same iPhone 18 Pro / iOS 27.0 simulator: PASS before commit. Freshly installed simulator launch results recorded below.
- Diff/secret checks occur before commit; hosted checks follow publication.

Physical Bluetooth/headset route changes, real microphone-to-detector delivery, vendor release/feature-buffer behavior and ASR handoff remain unverified. The passing acoustic settings from PR #28 are unchanged. No inference/model readiness bypass, package installation, microphone enablement or cloud service is introduced.

## Reproduce and next step

From the Git root, run `swift test --package-path Eilo/packages/native-test-seam`. With the local JDK17/Android SDK environment, run `Eilo/apps/mobile/android/gradlew -p Eilo/apps/mobile/android :app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug --max-workers=2`. These tests use synthetic PCM and scripted keyword metadata, not acoustic recordings or physical route evidence.

Review this boundary fix, then continue the mobile vendor binding/bounded capture-worker checkpoint before VC-TURN-03. Main merge awaits Gemju Sherpa review. Unrelated S02_REVIEW.md edits remain preserved and excluded.

Pre-commit simulator check: installed the freshly built Debug app and ran `python3 -O Eilo/scripts/verify-ios-launch.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8 --dwell 10` from the Git root. All three ten-second fresh launches PASS. This is startup evidence, not a live route-change or microphone recognition test.
