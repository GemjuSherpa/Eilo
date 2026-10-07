# S05 iOS native wake binding review

VC-TURN-02 / F03 / A02. Base: reviewed PR #29 merge `66ced57`. Workflow: `task/s05-vc-turn-02-ios-binding` → `sprint/s05-wake-ios-binding` → PR to main, awaiting Gemju Sherpa review.

Previously only the macOS C++ evaluation called the real vendor decoder; the Swift keyword interface had no vendor implementation. `NativeWakeStream` now binds the C ABI, owns/destroys its opaque handle exactly once and maps its fixed wake result to the existing keyword interface. C++ performs decode/reset synchronously; Swift exposes no transcript or retained PCM. The adapter rechecks verification around opening, input and result reads, and closes on invalid/changed-rate input, errors or revoked verification. Unsupported phrases and NUL/relative/oversized paths fail before C creation. Existing native generation/detector leases remain authoritative.

The app compiles this shared binding, but its real C implementation requires a Debug-only evaluation flag/import and separately verified assets. The offline verifier produces a local ARM64 simulator xcconfig rather than introducing mandatory remote dependencies or distributing vendor/model binaries. Standard builds retain unavailable defaults. No model-ready bypass, consent choice, permission request, capture connection, ASR, cloud inference or paid service was added.

## Validation before commit

| Check | Actual result |
|---|---|
| `swift test --package-path Eilo/packages/native-test-seam` | PASS: 84 XCTest tests, including six new handle/trust/error/path/input/deinit tests |
| `python3 Eilo/packages/wake-runtime/test_ios_integrity.py` and `python3 -O ...` | PASS: four integrity tests in each mode; changed archives/runtime/model/WAV, missing artifacts and incomplete acceptance sets rejected |
| `python3 Eilo/packages/wake-runtime/check_ios.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8` | PASS: exact archive and extracted-file hashes; C++17 `-Wall -Wextra -Werror` compilation for device/simulator; Swift simulator compilation/linking; real iOS decoder scores all 28 frozen entries |
| Real iOS runtime acceptance | PASS on limited synthetic set: 11 wake detections, zero activations among 15 nonwake entries; two diagnostics excluded; 24 unique WAVs from one voice; closed input rejected after every fixture |
| Local unsigned Debug app with generated `WakeEvaluation.xcconfig` | BUILD SUCCEEDED on the same iPhone 18 Pro / iOS 27.0 simulator; iOS 18 evaluation deployment floor; C ABI symbols verified in linked app |
| Installed evaluation app, `python3 -O Eilo/scripts/verify-ios-launch.py --udid ... --dwell 10` | PASS: three fresh launches, each alive after ten seconds; no microphone use/consent changes |
| Normal Debug app without xcconfig | BUILD SUCCEEDED; no vendor C ABI symbols present; installed and three ten-second launches PASS; standard app left running |
| Staged diff and secret scan | PASS: `git diff --cached --check`; `gitleaks git . --staged --redact=100 --no-banner --log-level error --config .gitleaks.toml` |
| Hosted checks | Pending at PR publication; fixture integrity tests added to existing CI |

Reproduction, exact downloads/checksums and evaluation-build command: [runtime README](../../packages/wake-runtime/README.md). [Recorded simulator results](../../packages/wake-runtime/tests/ios-results.json) contain scalar synthetic evidence only. Binaries, model weights, WAVs, absolute-path build configuration and build outputs stay ignored under `.local`/native build directories. No full fixture regeneration is claimed; all scored frozen hashes were verified.

## Remaining gates

VC-TURN-02 remains partial. Android vendor binding, verified production model-pack selection/trust and lifetime pinning, bounded capture-worker delivery/resampling, physical speaker/noise/audio-route calibration and vendor feature-buffer retention/erasure are still open. Device C++ compilation is not physical-device execution, and simulator file decoding is not app microphone recognition or an ASR pass. Distribution rights/transitive licensing remain a release gate; linking for local evaluation does not authorize publication of these artifacts. VC-TURN-03 stays dependency-blocked until the relevant native integration is complete.

Unrelated `S02_REVIEW.md` edits are preserved and excluded. Main merge awaits Gemju Sherpa review. Next checkpoint: bounded iOS capture delivery into the verified wake stream; Android binding remains separately required.
