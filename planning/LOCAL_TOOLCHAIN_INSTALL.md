# Local development tool installation

Date: 2026-10-05. Owner authorized downloading and installing necessary local development tools. This does not authorize app scaffolding, feature development, remote provisioning or deployment.

## Installed and verified

- Homebrew OpenJDK 17.0.20; direct `java -version` passed.
- Watchman 2026.07.27.00; `watchman --version` passed.
- CocoaPods 1.17.0; `pod --version` passed. Project compatibility still requires validation after React Native is pinned.
- Android Studio 2026.1.3.8 (Apple Silicon), installed at `/Applications/Android Studio.app`; bundle metadata verified.
- Android command-line tools build 15859902; SDK manager version 22.0 passed with Java 17. SDK manager reports deprecation in favor of the new Android CLI.
- Android SDK at `/Users/gemju/Library/Android/sdk`: platform Android 35 revision 2, Build Tools 36.0.0, platform-tools 37.0.1, emulator 37.2.12.
- ADB version and aapt2 version passed. Emulator version passed outside the sandbox; sandbox CPU feature detection produced a false incompatibility report.
- Existing Node 24.11.1 / npm 11.6.2 retained; version checks passed.

Homebrew installed supporting dependencies and upgraded pcre2 and sqlite as required. Standard Android SDK installation license accepted during the explicitly authorized CLI installation.

## Configuration

An Eilo Java/Android environment block was appended to `/Users/gemju/.zshrc`, preserving existing content. New interactive shells use JDK 17 and the SDK above. Existing terminals can run `source ~/.zshrc`.

## Pending / not verified

- Full Xcode is required for local iOS SDK/compiler/simulator builds. Standalone Apple Command Line Tools are already present but insufficient. Computer-use access to App Store was denied; owner must install Xcode from Apple's Mac App Store and complete first-launch platform components.
- Android ARM64 virtual-device system image/AVD not installed or booted. Select during native setup, or use a physical Android phone.
- React Native version, Android NDK and CMake versions remain unselected. Install matching native components when the project version is pinned rather than inventing a compatibility claim now.
- No app scaffolding, builds, simulator/device tests or deployment performed. Native readiness is partial, not a clean-build pass.
- No Git staging, commits, pushes or other repository writes performed in this installation task.

State: awaiting owner review of local tool installation.

## Xcode follow-up verification

Xcode 27.0 build 27A266a is installed at `/Applications/Xcode.app`. Explicit `DEVELOPER_DIR` checks confirm iOS 27.0 and iOS Simulator 27.0 SDKs. First-launch status check passed. Outside-sandbox `simctl list runtimes` confirms iOS 27.0 runtime (24A434). No simulator boot or app build performed.

The global developer path still points to `/Library/Developer/CommandLineTools`. Switching with `sudo -n xcode-select --switch /Applications/Xcode.app/Contents/Developer` requires the owner's administrator password and did not change the path. Owner can execute that command interactively in Terminal. Scoped commands can already use `DEVELOPER_DIR=/Applications/Xcode.app/Contents/Developer` without changing the global path.
