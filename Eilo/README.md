# Eilo

Local React Native New Architecture scaffold, without Expo. Mobile source and native projects are in `apps/mobile`. The launch shell shows Eilo / Guest / Stopped. Conversation features are not implemented.

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

Local debug builds and guest-shell launches passed on Android API 35 ARM64 emulator and iPhone 18 Pro / iOS 27 simulator. Xcode 27 launch wiring uses UIScene. This verifies the guest shell only.

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

Node 24.11.1 / npm 11.6.2 were used. One npm workspace lockfile pins dependency resolution. Metro and Android Gradle paths support hoisted dependencies. Jest tests the React Native shell. Vitest tests the metadata-only contract in packages/contracts. Kotlin JUnit and Swift XCTest exercise native fake-adapter seams; no production controller exists yet.

The generated `com.eilo` identifiers and template Android debug signing are local scaffold defaults, not approved release identity/signing. No account, microphone capture, model runtime, backend or cloud resources have been added. Parent AGENTS.md and architecture/review instructions apply. Do not stage, commit or push; owner review is required before the next task.

## S01 review

See docs/sprints/S01_REVIEW.md and docs/verification/DEVICE_WORKLOAD_MATRIX.md. All changes remain uncommitted on sprint/s01-foundation. The Android release shell has no Internet or microphone permission; debug builds permit Metro. Local release-mode builds use test signing only and are not distribution artifacts. CI is drafted for public-repository standard runners; its first hosted run remains pending owner push/PR. Private-repository jobs are intentionally skipped until a new cost/security review.
