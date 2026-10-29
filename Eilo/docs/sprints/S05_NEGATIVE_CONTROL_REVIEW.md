# S05 direct-ASR noise-only control review

This independent VC-TURN-06/VC-TURN-10 diagnostic follows the frozen speech/noise calibration pilot. The protocol and collector wrapper were committed at `29bcbe9f00ef079d6e69e4292ec5eeb4f278f1b5` before inference. The previous private development calibrator, diagnostic cutoff (0.85), model, runtime and native collector were reused unchanged; no fitting or threshold selection occurred. No ordinary-app runtime was activated.

Inputs were the twelve previously approved, normalized MUSAN noise-category clips, three digital-silence controls (1/5/10 seconds), and three deterministic uniform-noise controls (three seconds; peak PCM values 328/3277/9830). The uniform levels share a waveform derived from seed 20261029. MUSAN component inventory licenses and receipt remain pinned; no new data, model, package, account or terms were requested. No audio, transcript, case score or private model knot is committed or uploaded.

The MUSAN inputs were already used in earlier mixtures, not selected as a fresh holdout. Their labels are weak corpus categories and do not establish verified absence of speech. Synthetic inputs contain no speech by construction. The three noise amplitudes and silence durations are correlated controls, not independent draws. All 120 examined clean speech clips remain consumed; this experiment introduces no new clean-speech evaluation cohort. Model-training overlap remains UNKNOWN.

## Actual native observations

One isolated Android API35 ARM64 emulator build executed all eighteen file-fed inputs and rejected empty, unaligned, nonfinite and out-of-range float inputs. Before/after source, model and reconstructed input hashes agree. Emulator audio was disabled; scratch audio was removed and the owned emulator stopped. No physical phone, microphone, normal app installation or permission change occurred.

Both decoder paths produced the same aggregate outcome:

| Group | Cases | Available scores / observed word-bearing outputs | Unavailable scores | Raw / mapped word-bearing outputs accepted at 0.85 |
| --- | --- | --- | --- | --- |
| MUSAN weak noise categories | 12 | 0 / 0 | 12 | 0 / 0 |
| Digital silence | 3 | 1 / 1 | 2 | 0 / 0 |
| Synthetic uniform noise | 3 | 0 / 0 | 3 | 0 / 0 |

One digital-silence control generated word-bearing text in both paths, below the fixed raw and mapped cutoff and outside the development score range. Greedy unavailable cases reported EOS_WITHOUT_USABLE_SCORES; their dependent self-draft cases reported GREEDY_UNAVAILABLE. The public API does not expose their text outcome, so all seventeen remain TEXT_OUTCOME_NOT_OBSERVABLE. Unavailable scores are not zero confidence, verified silence detection, or successes. Counts retain every input within its own group denominator.

The zero accepted count is a small direct-ASR observation, not a zero-risk guarantee. No WER, correctness/calibration metric, VAD quality or end-to-end false-activation rate is computed. VAD and wake gates are bypassed. Applying the speech-correctness mapping to noise is a mechanical stress probe, not a probability of speech presence or production suitability. These results must not refit the model or qualify the threshold.

## Verification and remaining gates

Twenty-eight package tests pass in normal and optimized Python with no skips, including native-response validation, group denominators, unavailable outcomes, forbidden promotion, frozen protocol/model/source checks, and aggregate-only export/no-overwrite behavior. The actual native build is about 22 MiB, within the approved local prototype budget. CI validates the committed aggregate report without corpora/models and uploads only JSON/HTML summaries for seven days. The full offline workflow and all exact-head hosted checks remain required before merge.

VC-TURN-06/VC-TURN-10 acceptance remains open. Native calibration NOT_ESTABLISHED, threshold authorization NOT_GRANTED, production confidence NOT_ENABLED, physical tests OPEN / NOT_RUN, S08/release HOLD and persistent memory DISABLED are unchanged. Further progress requires the separate streaming/caller integration and physical or representative evaluation prerequisites; this diagnostic does not close them.
