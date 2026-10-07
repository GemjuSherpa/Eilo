# S05 — Hey, Eilo acoustic correction

VC-TURN-02 / F03 / A02. Gemju Sherpa requested diagnosis and correction of the two wake misses and clarified the activation phrase as **Hey, Eilo**, with the previously selected **Ay-loh** pronunciation. Task/s05-vc-turn-02-acoustic continues sprint/s05-wake-validation and updates its existing review PR #28. Main is af5e916 after reviewed PR #27; the fixture-validation checkpoint is retained in this PR.

## Cause and correction

The previous decoder used `HEY ALO`, four active paths, threshold 0.1 and boost 3. The failure was acoustic decoding configuration, not an ASR exception: ordinary `Hello Ailo` could be pushed into the keyword path while the paused target and a target followed by a question were missed. ASR has not been connected to this evaluation adapter, and its task depends on wake integration rather than compiler success.

Select phonetic tokens `▁HE Y ▁A ▁LO W` (`HEY A LOW`), eight active paths, one trailing blank, threshold 0.125 and boost 1.5. The phrase remains Hey, Eilo; the phonetic spelling is a model-internal representation of Ay-loh. The fixed output label remains HEY_EILO. The wrapper still accepts only bounded native PCM, resets/consumes results per decode, emits no transcript and fails closed on invalid inputs. No filename-specific decisions, raw recording collection or expected-label changes were added.

A local lexicon/parameter exploration evaluated the actual pinned runtime, beginning with the previously failing samples. In the recorded search, lexicon `HEY A LOW` at eight paths / 0.1 / 1.5 resolved the original three failures but activated on `Hey alone`. Raising the threshold to 0.125 eliminated that activation while preserving all original wake detections. That candidate passed all original acceptance entries before additional comma-pause fixtures were generated.

Controlled ablations at threshold 0.125 retain the other selected settings:

| Restored setting | Observed regression on focused samples |
| --- | --- |
| Four active paths | Paused `Hey, ay low` missed |
| Previous boost 3 | Both original wake misses and `Hello Ailo` activation return |
| Previous `HEY ALO` tokens | `Hey alone` activation returns |

These measurements establish regressions on these synthetic samples, not a universal causal model of natural speech. [Official decoder documentation](https://k2-fsa.github.io/sherpa/onnx/kws/index.html) explains keyword boost and probability threshold; the exact selected values come from local measurements.

## Actual verification

- C++17 `-Wall -Wextra -Werror` and scripted ABI contract with ASan/UBSan: PASS. Contract asserts the exact phonetic tokens, active paths and trailing-blank settings to catch decoder configuration drift.
- Eight fixture validation tests: PASS under normal and optimized Python.
- `python3 packages/wake-runtime/check_host.py`: exit 0, **PASS ON SYNTHETIC SET ONLY**. All original seven wake and eleven nonwake entries pass, followed by four additional paused wake and four paused/nonwake entries. Total: eleven wake detections, zero activations across fifteen nonwake entries; two diagnostic controls excluded. 28 entries / 24 unique waveforms, one synthetic voice. No frozen original samples/hashes/expected labels removed or changed.
- Pinned archives, extracted runtime/model files and all fixture hashes/format/energy checks: PASS. Generated audio remains local and ignored. Historical failures and partial searches are preserved in `tests/acoustic-tuning-results.json`; current full results are in `tests/results.json`.
- Unsigned Debug Xcode build on the same iPhone 18 Pro / iOS 27.0 simulator: PASS before commit. Launch checks and fixture regeneration are recorded below after completion.

## Remaining work and reproduction

This removes the reported acoustic failure on the frozen synthetic set. It does not make the simulator listen or run ASR: mobile vendor bindings, verified asset readiness and bounded capture-worker integration are still absent. Physical speaker/noise calibration, lifetime/resampling and distribution-trust checks remain open. VC-TURN-02 remains partial; VC-TURN-03 must not be called dependency-complete until those integration gates are addressed. Next dependency-ready work is the native mobile runtime/binding checkpoint using these corrected settings, followed by the ASR handoff.

From Eilo, run `python3 packages/wake-runtime/test_fixture_validation.py`, then `python3 packages/wake-runtime/check_host.py` with the pinned local assets described in the runtime README. Expected exit is now 0 on this set. The reproduction limitations of the installed voice remain. No model-readiness bypass, ambient transcription, microphone/network connection or paid service was introduced. Main merge awaits Gemju Sherpa review; unrelated S02_REVIEW.md edits remain excluded.

Pre-commit live check: installed the freshly built Debug app, then `python3 -O scripts/verify-ios-launch.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8 --dwell 10` passed all three fresh launches. No simulator reset/consent change or microphone capture. Hosted checks follow publication.

Fixture regeneration limitation: a full repeat stalled in installed Samantha `say` while generating the existing ordinary-speech sample. The Eilo-only child was terminated; regeneration was not completed and is not a pass. All 28 actual scored WAVs had passed manifest SHA256/format/energy verification. Both voice generation and conversion now have 30-second deadlines so this limitation fails explicitly instead of hanging. Newly added eight samples were generated successfully before selection validation, but full future reproduction remains dependent on the local voice/tool state.
