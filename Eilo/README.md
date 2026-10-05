# Eilo

Local React Native New Architecture scaffold, without Expo. Mobile source and native projects are in `apps/mobile`. This is the official sample screen, not implemented Eilo product behavior.

## Commands

From this directory:

```sh
npm ci
npm run lint
npm run typecheck
npm test -- --watchman=false
npm start
```

## Native development

Local debug builds and sample-screen launches passed on Android API 35 ARM64 emulator and iPhone 18 Pro / iOS 27 simulator. Xcode 27 launch wiring uses UIScene. This verifies the sample scaffold only.

Open a new terminal (or `source ~/.zshrc`) for configured Java, Android SDK and Homebrew Ruby paths. To develop:

```sh
npm start
# In a second terminal:
npm run android
# Or, with an iOS simulator:
npm run ios
```

Android virtual device `Eilo_API35` is available. Build dependencies: API 37.0, Build Tools 37.0.0, NDK 27.1.12297006, CMake 3.22.1. For iOS, use `apps/mobile/ios/Eilo.xcworkspace`. Reinstall native dependencies after relevant dependency changes:

```sh
cd apps/mobile
bundle install
cd ios
bundle exec pod install
```

Gemfile.lock and Podfile.lock record resolved native dependency versions. Metro uses its filesystem watcher because Watchman stalled during verification.

Node 24.11.1 / npm 11.6.2 were used. One npm workspace lockfile pins dependency resolution. Metro and Android Gradle paths support hoisted dependencies. The template's Jest runner is used only for React Native UI tests; no services or pure-logic packages exist yet.

The generated `com.eilo` identifiers and template Android debug signing are local scaffold defaults, not approved release identity/signing. No account, microphone capture, model runtime, backend or cloud resources have been added. Parent AGENTS.md and architecture/review instructions apply. Do not stage, commit or push; owner review is required before the next task.
