# Project scaffold review

Authorized scope: create the local project under Eilo. Execution-plan Stage 1(a) scaffold baseline, linked as partial prerequisite work to VC-BASE-01 and VC-BASE-02 (F13/A10); neither native launch acceptance is complete.

## Result

Official React Native 0.87.1 / Community CLI 20.2.0 TypeScript template; Kotlin Android and Swift iOS projects; npm workspace with one lockfile, exact direct dependency pins, strict TypeScript, workspace scripts, hoisted Metro/Android dependency paths. Sample screen retained. No product features implemented.

## Checks

- Active developer path: /Applications/Xcode.app/Contents/Developer; Xcode 27.0.
- Node 24.11.1, npm 11.6.2, Java 17.0.20, CocoaPods 1.17.0 verified.
- npm run lint: PASS.
- npm run typecheck: PASS.
- npm test -- --watchman=false: PASS, one scaffold render smoke test.
- React Native CLI config: PASS, native directories and workspace React Native path resolved.
- Initial nested install caused lint plugin resolution failure; replaced with standard hoisted installation and reran checks successfully.

## Not run / limitations

Android Gradle compilation/install/launch and iOS pod installation/compilation/launch were not run in this scaffold-only step. No physical device, lifecycle, privacy, audio, offline or model tests performed. Tool presence and JS checks do not prove native compatibility. SDK/Build Tools 37 and NDK 27.1.12297006 are missing from the earlier general Android tool installation. iOS template Ruby dependency constraints require compatibility verification against Xcode 27.0 before installation. CLI upstream compatibility table lags the release; template itself selects CLI 20.2.0 and config resolves, but native compatibility remains unverified. Template dependencies report upstream deprecations; no vulnerability/security clearance claimed. No Git repository initialized, staged, committed or pushed.

## Dependency inventory

| Dependency | Version | License |
|---|---|---|
| react | 19.2.3 | MIT |
| react-native | 0.87.1 | MIT |
| @react-native/new-app-screen | 0.87.1 | MIT |
| react-native-safe-area-context | 5.10.1 | MIT |
| @babel/core | 7.29.7 | MIT |
| @babel/preset-env | 7.29.7 | MIT |
| @babel/runtime | 7.29.7 | MIT |
| @react-native-community/cli | 20.2.0 | MIT |
| @react-native-community/cli-platform-android | 20.2.0 | MIT |
| @react-native-community/cli-platform-ios | 20.2.0 | MIT |
| @react-native/babel-preset | 0.87.1 | MIT |
| @react-native/eslint-config | 0.87.1 | MIT |
| @react-native/jest-preset | 0.87.1 | MIT |
| @react-native/metro-config | 0.87.1 | MIT |
| @react-native/typescript-config | 0.87.1 | MIT |
| @types/jest | 29.5.14 | MIT |
| @types/react | 19.3.0 | MIT |
| @types/react-test-renderer | 19.3.0 | MIT |
| eslint | 8.57.1 | MIT |
| jest | 29.7.0 | MIT |
| prettier | 2.8.8 | MIT |
| react-test-renderer | 19.2.3 | MIT |
| typescript | 6.0.3 | Apache-2.0 |

Official template dependencies retained for scaffold compatibility; exact transitive resolution is in package-lock.json. Future navigation/state/services are intentionally deferred to assigned tasks.

State: awaiting human review, native verification partial. Next suggested task: Android toolchain completion and clean build, separately authorized.

## Remaining setup completed — 2026-10-05

Owner authorized completion of local setup. Installed Android platform `android-37.0` revision 2, Build Tools 37.0.0, NDK 27.1.12297006, CMake 3.22.1, Google APIs ARM64 API 35 image, and SDK-local command-line tools. Created `Eilo_API35` AVD. Final shell paths prefer SDK-local tools and Homebrew Ruby 4.0.6.

Bundler 4.0.16 installed the template's Ruby dependencies into ignored vendor/bundle; locked CocoaPods 1.15.2 and xcodeproj 1.25.1. Pod install succeeded: 86 pods. Generated Xcode workspace and native lockfiles. This combination built successfully with Xcode 27.0 on this Mac.

Actual verification:
- Android `JAVA_HOME=... ANDROID_HOME=... ./gradlew :app:assembleDebug --max-workers=4`: BUILD SUCCESSFUL, 3m40s. APK: Eilo/apps/mobile/android/app/build/outputs/apk/debug/app-debug.apk.
- iOS `xcodebuild -workspace Eilo.xcworkspace -scheme Eilo -configuration Debug -sdk iphonesimulator -destination 'generic/platform=iOS Simulator' -derivedDataPath build/DerivedData CODE_SIGNING_ALLOWED=NO -jobs 4`: BUILD SUCCEEDED.
- Initial iOS launch failed at UIKit's missing-scene-lifecycle check. Added SceneDelegate/window startup in AppDelegate.swift and UIApplicationSceneManifest in Info.plist, rebuilt successfully, installed and launched on iPhone 18 Pro iOS 27.0. Visually verified sample screen and Hermes JavaScript runtime.
- Android APK installed successfully on API 35 ARM64 emulator, ADB reverse configured for Metro, MainActivity launched; process remained running and screenshot visibly confirmed sample screen.
- Metro initially waited indefinitely on Watchman. Configured resolver.useWatchman=false; filesystem watcher bundled successfully.
- Final npm lint, strict typecheck and one render smoke test: PASS.

Screenshots: planning/ios-scaffold-launch.png and planning/android-scaffold-launch.png. Raw diagnostic logs were temporary under /tmp/eilo-*.log. No physical-device testing, signed distribution, traffic/privacy audit, empty guest shell or product behavior acceptance claimed. BASE-01/02 remain partial prerequisites awaiting review. Template's debug Internet permission and sample links are development scaffolding, not an offline-core pass. No Git staging, commits, pushes, provisioning or deployment.

Local setup complete; stop for owner review before feature development.
