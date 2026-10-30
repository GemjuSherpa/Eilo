# S05 iOS exposed-reference diagnostics

## Scope

The iOS replay exercises the already reviewed Moonshine 0.1.5 streaming collector and the same two score paths used by the existing Android corpus diagnostic. It uses only the previously cached Common Voice clips, the previously exposed 30-case cohorts, their 90 correlated noise variants, 12 MUSAN weak-noise clips, and 6 deterministic synthetic silence/noise controls. The replay freezes protocol and source hashes before inference, checks the approved source/model/archive before and after collection, builds an ARM64 iOS Simulator executable, relocates it, and rejects four malformed audio inputs.

The checked-in result is aggregate-only. It contains no audio, transcript, speaker, clip identifier, or per-case score. The private local run record retains only temporary numeric rows and was not exported. CI validates the committed aggregates and creates a seven-day aggregate-only JSON/HTML artifact; CI does not access datasets, models, native caches, microphone input, or hardware.

## Observations

Across the seven clean/noise groups, each source returned 203 of 210 scores. This count includes repeated observations from overlapping previously exposed cohorts and correlated noise variants; it is not 203 independent examples. At the diagnostic raw score cutoff of 0.85, the 0 dB group accepted 20 greedy-path and 18 self-draft-path observations, with 10 and 9 exact-match errors respectively. The cutoff therefore does not provide a safe acceptance rule.

For the six negative-control group/source combinations, the 12 MUSAN weak-noise clips and six uniform-noise clips had no usable scores. Two of three digital-silence clips were unavailable on both paths. One available silence clip produced word-bearing text on both paths, but neither score reached 0.85. These controls do not measure end-to-end false activation: VAD was bypassed, and the corpus labels for MUSAN are weak.

All results are diagnostic only. The data was previously exposed, Common Voice model-training overlap is unknown, and no fitting or threshold selection occurred. Native calibration remains NOT_ESTABLISHED, threshold authorization NOT_GRANTED, physical testing NOT_RUN, production NOT_ENABLED, release HOLD, and persistent memory DISABLED.

## Reproduction

The native inference run was completed on the existing iOS Simulator using the frozen protocol and approved local caches. To validate only the aggregate evidence (no corpus/model/native cache access), run from `Eilo/packages/dataset-evaluation`:

```sh
python3 -m unittest discover -s ../asr-ios-corpus -p 'test_*.py' -v
python3 -O -m unittest discover -s ../asr-ios-corpus -p 'test_*.py' -v
python3 ../asr-ios-corpus/reference_report.py --output /tmp/asr-ios-reference
```

The JSON and HTML exports omit binary/source hashes and all per-case fields.
