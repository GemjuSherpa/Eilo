# Eilo

React Native CLI mobile workspace. S01 foundation is merged; Gemju Sherpa approved S02. S03 adds verified native model installation and readiness; its review is pending. The current app displays the Guest/Stopped shell. Real voice capture, ASR, wake/VAD, model replies and offline TTS are not integrated. No production model host or signing key is configured.

## Run locally

From this directory, keep Metro running in one terminal:

```sh
npm start
```

In another terminal:

```sh
npm run ios -- --simulator="iPhone 18 Pro"
# Or, after starting an Android emulator:
npm run android
```

For a connected iPhone, open apps/mobile/ios/Eilo.xcworkspace in Xcode, select the Eilo scheme/device and configure your signing team, then Run with Metro running. Expo Go is not used. Existing native dependencies are installed; a fresh checkout requires npm ci and the pinned Ruby/CocoaPods setup in apps/mobile. Node 24.11.1 and npm 11.6.2 were used locally.

## Verify

```sh
npm run lint
npm run typecheck
npm test
swift test --package-path packages/native-test-seam
```

Android native builds/tests use JDK17 and the Android SDK, with Gradle in apps/mobile/android. iOS uses Xcode and the installed Pods. Debug builds support Metro; release builds use local test signing on Android and unsigned simulator compilation on iOS. These are not distribution artifacts.

Native controller and installer own privacy/capture/readiness. No personal content or keys are persisted in JavaScript. Android Internet permission supports the isolated generic model downloader; production origins/trust/license approvals are empty. No cloud inference exists. Downloaded sources, isolated conversion tools and generated GGUFs live in ignored .local/model-build and are not uploaded to GitHub.

See [S03 review](docs/sprints/S03_REVIEW.md), [model recipe](tools/model-pack/README.md), [installer contract](docs/models/MANIFEST.md) and [blocking distribution review](docs/models/DISTRIBUTION_REVIEW.md). No paid service, deployment or later sprint is included.
