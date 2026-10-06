# S05 — iOS simulator launch crash correction

Gemju Sherpa reported the local simulator was not working and authorized rerunning and diagnosing the open iPhone 18 Pro. This fix is independent of the runtime evaluation in PR #26: sprint/s05-simulator-fix starts from reviewed main e8a8331, with task/s05-ios-simulator-fix as its task branch. PR #26 remains unchanged while under review. This is a regression in the existing VC-CTRL-08 native module/event bridge, not completion of wake recognition.

## Reproduced cause and correction

Metro was running and successfully serving the iOS bundle. The installed Eilo Debug app launched, rendered React Native, and exited. Two Eilo-only crash reports showed SIGABRT / `std::__throw_bad_function_call` from `NativeEiloControlSpecBase emitOnSnapshot`, called by the timer in `EiloControl init`.

The generated base invokes a C++ callback directly. Eilo previously started its timer during construction, before React Native supplied that callback; an instance without a JSI emitter could still poll and call the empty function. A successful unsigned compile had not exercised this runtime failure.

Eilo now starts the snapshot timer only after `setEventEmitterCallback` succeeds. Timer setup and Swift/UIKit snapshot reads run on the main thread. Callback installation, emission and invalidation share a synchronization boundary. Invalidation disables emission immediately, clears the callback and schedules timer cleanup on the main thread. A late setup cannot restart an invalidated module. No generated React Native files or dependencies are changed.

## Actual checks

- Reproduced the installed Debug app exiting and inspected Eilo-only exception frames; no raw crash report or device logs are published.
- Xcode unsigned Debug build targeting the already-booted iPhone 18 Pro / iOS 27.0 simulator: PASS. Existing React Native/Pods script warnings remain.
- Installed corrected Debug build locally and observed the Eilo onboarding screen instead of an app exit.
- Metro reload: app process remains alive after five seconds.
- Three fresh terminate/launch cycles: app process remains alive after five seconds each; onboarding screen stays visible.
- This is launch/bridge runtime evidence, not a physical phone, microphone, background, model or conversation-quality pass. Native model readiness and S05 wake-recognition gates remain closed. Interactive consent/navigation checks are not claimed while Device Hub UI permissions are unavailable.
- Rebuilt from the isolated fix branch based on main: Debug and Release compiler checks PASS. The committed smoke-check command passes three Debug launch cycles. Bundled Release launch also passes; the Debug app is restored and left running afterward. No simulator data reset, consent change or microphone capture was performed.
- Diff/secret checks and hosted publication status are recorded with the PR. Hosted checks will be pending when it is first opened.

## Reproduce

Keep Metro running from the Eilo mobile workspace. Build/install the Debug app on a chosen already-booted simulator, then run from Eilo:

```sh
python3 scripts/verify-ios-launch.py --udid YOUR_BOOTED_SIMULATOR_UUID
```

The script checks only the Eilo app, performs three fresh launches by default, waits five seconds each and verifies each launched PID is still present. It never erases/uninstalls the app or changes consent. It deliberately leaves Eilo running. Use `xcrun simctl list devices booted` to find the UUID. To check module teardown/reinitialization in development, issue one `POST http://localhost:8081/reload` against Eilo's running Metro server and verify the app remains open.

Review scope: event-emitter startup/teardown crash fix and reproducible launch check. Main merge awaits Gemju Sherpa review. The unrelated S02_REVIEW.md change is preserved.
