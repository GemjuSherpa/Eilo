# VC-TURN-02 — runtime evaluation and decode handoff review

Requirements F03/A02. Dependency VC-TURN-01 is approved. Gemju Sherpa reviewed the partial adapter checkpoint in PR #25 and authorized completing pending S05 Git steps and continuing project tasks on 7 October 2026. The reviewed checkpoint e8a8331 is now pushed to main; PR #25 is merged. This continuation uses task/s05-vc-turn-02-runtime → sprint/s05-turn-recognition → PR to main.

## Result

Gemju Sherpa selected **Hey Eilo**, pronounced **Ay-loh**. A reproducible macOS ARM64 evaluation now links the actual sherpa-onnx 1.13.8 C API and the official GigaSpeech 3.3M KWS candidate. Runtime/checkpoint hashes, an archived model license declaration, synthetic fixture provenance and failed acoustic results are recorded in `packages/wake-runtime`. Vendor/model binaries and system-voice WAVs remain local and ignored. Voice redistribution rights have not been established; public evidence contains source text/hashes/results, not generated voice audio. No mobile runtime dependency, production manifest trust, microphone consumer or model-readiness bypass was introduced.

Kotlin and Swift previously read the keyword only after draining every ready decode step. A transient trigger could be overwritten by a later step in the same frame. Both adapters now consume/reset each decode result and retain only a metadata match for the frame. They still reject the whole frame on backend/runaway failure and recheck cancellation/verification before activation. A new regression test on each platform demonstrates a wake in the first step followed by an empty second step. The C++ evaluation wrapper follows the same per-step result pattern and rejects sample-rate changes on an existing stream.

## Actual verification

- Android `:app:compileDebugKotlin :app:testDebugUnitTest :app:lintDebug --max-workers=2`: PASS; 85 tests, zero failures/errors/skips.
- `swift test --package-path Eilo/packages/native-test-seam`: PASS; 77 tests, zero failures.
- Common Swift source typecheck against iOS Simulator SDK, target arm64 iOS 18: PASS.
- Fixture validation: three Python regression tests PASS; empty/silent/wrong-rate audio is rejected before scoring. Initial silent TTS files and invalid scores were discarded and regenerated before freezing evidence.
- C++17 compilation with `-Wall -Wextra -Werror`: PASS.
- Scripted C ABI contract checks with address/undefined-behavior sanitizers: PASS. Covers transient results, unknown labels, result release, failed stream construction, invalid/null/oversized/nonfinite input, terminal failure, decode exception/cap, sample-rate change and destruction. These are contract tests, not acoustic evidence.
- Real CPU acoustic run at threshold 0.1/boost 3: **FAIL**. Five of seven intended target cases detect; two miss. Ten of eleven nonwake cases yield zero detections; `Hello Ailo` falsely activates. Two exploratory controls are recorded but excluded from acceptance scoring; one pronunciation control is detected. This cannot establish recognition of the requested pronunciation.
- Five exploratory threshold/boost pairs with the earlier `HEY A LOW` lexicon detect at most four of the initial five target fixtures. The revised `HEY ALO` candidate is tested on eight additional phrases generated after selection, from the same TTS voice. Some spelling variants yield identical waveforms. No calibrated production threshold or independent speaker/noise accuracy estimate results from that tuning.
- Unsigned iOS simulator Release app build: PASS. Existing template warnings remain. No signing, deployment or physical-device pass.
- Hosted checks: pending publication of this continuation.

## Reproduction and evidence

See [runtime evaluation](../../packages/wake-runtime/README.md) for the exact pinned downloads and `python3 packages/wake-runtime/check_host.py`. It performs no download, microphone capture or package installation. Current exit code 1 deliberately signals failed acoustic acceptance. [Frozen results](../../packages/wake-runtime/tests/results.json), [exploratory results](../../packages/wake-runtime/tests/exploratory-results.json) and [fixture manifest](../../packages/wake-runtime/tests/fixtures/manifest.json) preserve the actual outcomes and synthetic source text.

Compiler/contract checks passing must not override the failed recognition result. The fixtures are synthetic macOS TTS from one voice, not recordings or a representative speaker/noise/device dataset. No conversational inference backend is linked or invoked by this native harness; no production end-to-end model-call-count claim is made.

## Remaining gate

The tested lexicon/checkpoint combination fails this target/nonwake fixture set, including a confusable nonwake activation. Further pronunciation/checkpoint evaluation is required before capture integration. The model digest is locally observed from official HTTPS, unlike the publisher-supplied runtime digest; production trust and distribution-license review remain incomplete. Mobile ABI packaging/bindings, resampling, vendor feature-buffer lifetime/erasure, bounded worker delivery and physical phone tests remain unverified. No raw-user-audio debugging, cloud inference or readiness weakening is proposed.

Tracker: VC-TURN-02 remains partial, acoustic acceptance failed, awaiting review of this continuation. VC-TURN-03 stays dependency-blocked. Main merge of this continuation awaits Gemju Sherpa review. The unrelated S02_REVIEW.md edit is preserved and excluded.
