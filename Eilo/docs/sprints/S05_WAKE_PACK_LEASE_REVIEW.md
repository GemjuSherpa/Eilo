# S05 / VC-TURN-02 — Android signed wake-pack lease

10 October 2026. Gemju Sherpa reviewed/merged PR #34; verified base main `63980aa`. This is a partial VC-TURN-02 checkpoint (F03/A02), awaiting review. VC-TURN-03 remains gated.

Previously native wake construction accepted independently verified paths without an adapter to the existing signed pack store. `WakePackLease.resolve` now obtains a serialized verified snapshot from `PackStore`, checks the expected pack/runtime, and selects the encoder, decoder, joiner and token file by four distinct configured IDs and exact SHA256 pins. Model files require the wake role and `.onnx`; tokens require tokenizer and `.txt`. Manifest order cannot change selection. Existing signature, configured trust, platform/runtime, license-evidence, path/symlink and file-integrity checks apply before resolution. The store verifies all artifacts once, rather than repeating a whole-pack hash pass for each selected path.

Resolution belongs on a native installer/inference worker. The lease captures the store epoch before resolving and rejects a replacement during resolution. Borrow-time verification is disk-free: it checks explicit revocation and the store epoch. Activation attempts, including rejected rollback, conservatively invalidate existing leases. The current store epoch is process-wide, so changes to another store also revoke a lease. Native stream verification before/after opening and decoding prevents publishing results from a revoked lease and releases unpublished handles. The caller owns and must close its decoder/delivery; lease close revokes use but does not itself destroy a decoder or wait for an in-flight borrow.

Slots must remain app-private and immutable. This lease is not an OS file lock or continuous external-mutation detector: before known maintenance/corruption changes, revoke the lease and close delivery/decoder. Initial resolution rejects already-corrupted or symlinked artifacts; arbitrary external tampering after resolution is outside the epoch guarantee. No arbitrary path/profile is accepted from JavaScript, and no production profile, trust key, signed pack, model download or automatic attachment is introduced. A native reviewed selection is still required; accepting a signed manifest alone does not select a model. The unavailable default JNI API and app model readiness remain unchanged. Runtime loading/packaging, production trust/selection and worker attachment, licensing/vendor retention and physical microphone/route/noise/latency gates remain open before ASR.

## Validation before commit

- Android compiler/lint and Debug/Release builds PASS with installed JDK 17, Android SDK and cached dependencies.
- 111 normal JUnit tests PASS, zero failures/errors/skips. Six new tests use synthetic four-byte assets, actual P-256 signatures, the actual pack store and a scripted native API. They cover shuffled ordering and correct paths; unavailable defaults; missing/wrong pack/runtime/hash/role/IDs; replacement and failed activation; replacement during opening; revocation during decode; idempotent handle cleanup; corrupted file and symlink rejection.
- Same booted iPhone 18 Pro / iOS 27.0 simulator (`E01AE333-A393-48F6-AAD7-579F0A5DB1F8`): normal Debug build and three fresh ten-second launches PASS. Consent/device data preserved.
- Staged diff check and staged Gitleaks secret scan PASS; only the five task files staged.
- Real decoder acoustic fixtures were not rerun: this checkpoint changes pack selection/lifetime, not JNI or decoding. PR #33 evidence is retained unchanged.
- Android device/AudioRecord execution and physical performance NOT RUN; no Android device is available. No production-ready pack/readiness/ASR success is claimed.

Reproduce Android checks from the repository root:

```sh
JAVA_HOME=/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home \
ANDROID_HOME=/Users/gemju/Library/Android/sdk \
Eilo/apps/mobile/android/gradlew -p Eilo/apps/mobile/android \
  :app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug \
  :app:assembleDebug :app:assembleRelease --offline --max-workers=2
```

Simulator: build the normal Eilo workspace/scheme Debug configuration for that already-booted simulator, install the generated app, then run `python3 -O Eilo/scripts/verify-ios-launch.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8 --dwell 10`. Logs: `/tmp/eilo-wake-pack-final.log`, `/tmp/eilo-wake-pack-ios-build.log`, `/tmp/eilo-wake-pack-ios-launch.log` (local temporary evidence).

Source control: `task/s05-vc-turn-02-wake-pack-lease` → `sprint/s05-wake-pack-lease` → PR to main, awaiting Gemju Sherpa review. Preserve/exclude unrelated `S02_REVIEW.md` edits. Next checkpoint: verified native runtime loading/worker attachment, while production trust and physical gates remain explicit.
