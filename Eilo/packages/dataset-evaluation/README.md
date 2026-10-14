# Public corpus evaluation (VC-DATA-01–05)

Desktop evaluation tools, separate from the mobile production pipeline. Public audio, derived
clips, transcripts, receipts and result files belong under `Eilo/.local/datasets/` (ignored).
Do not commit or upload audio, speaker identifiers or transcripts. No automatic downloader,
account login, archive extraction, model provisioning or cloud inference is added.

VC-DATA-01 registry checks publisher licensing and access separately. Common Voice English
release remains UNSELECTED: review the specific MDC dataset card/datasheet, obtain user
account/terms authorization, pin version/URL/checksum, and then record permission. CC0 does
not override MDC no-rehosting terms. MUSAN is CC BY 4.0 (SLR17, 2015); retain corpus and
per-file attribution. Speech Commands 0.02 is CC BY; verify its archive LICENSE before use.
Official source and access links are in registry.json. User approved MUSAN/Speech Commands
downloads on 14 October 2026. No Common Voice account terms have been accepted here.

Run from this directory:

```sh
python3 manifests.py
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 manifests.py --dataset musan --archive ../../.local/datasets/musan.tar.gz \
  --license-evidence ../../.local/datasets/musan/LICENSE \
  --output ../../.local/datasets/musan-receipt.json
```

Receipts stream SHA-256 and record size plus license-evidence hash. LOCAL_OBSERVED establishes
repeatability only, not publisher authenticity. Compare publisher checksums when available;
never invent one. Reverify receipts before extracting archives with a separately reviewed safe
extractor. Reject traversal/symlinks; preserve licenses outside the evaluation sample index.
Physical capture, device latency, interruption, standby, endurance and screen-off gates remain
NOT_RUN. Corpus scoring cannot change those gates or approve production model readiness.

VC-DATA-02: `preprocess.py --dataset speech_commands --root <local extracted corpus>
--receipt <receipt.json> --output <new ignored directory> --split test --limit 100 --seed 0`.
Official testing/validation lists and CV test/dev TSVs determine held-out membership; train
is rejected. No new random train/test split. Seeded SHA-256 ordering fixes sample selection,
IDs anonymize source/speaker names, and normalized WAV plus PCM hashes freeze input. WAV
PCM 8/16/24/32-bit mono/stereo converts to 16 kHz PCM16; integer area averaging on downsample
and linear interpolation on upsample are a reproducible desktop baseline, not a high-fidelity
production resampler. No gain normalization, trimming, padding or transcript-changing crop.
MUSAN noise-only clips use first 30s; they do not supply speech-positive VAD labels. CV MP3
requires separately provisioned ffmpeg binary hash; decoding rejects duration-limit clips.
Record decoder version/license with its hash in local receipts; no decoder is installed here.
Full extracted corpus receipts/licenses remain local; index receipts pin the approved archive.

VC-DATA-03: `benchmark.py --manifest <frozen/manifest.json> --output <local/report.json>`
produces NOT_RUN with no adapter. Add `--adapter <local executable> --adapter-metadata
<local metadata.json>` to run or `--predictions <local predictions.json>` to score saved
results. Each adapter receives request/response JSON paths; request has schema_version=1,
id, task, audio (absolute frozen WAV), rate=16000. Response has id and transcript for ASR;
commands also requires command (ten target words, unknown or silence); VAD uses sorted,
non-overlapping [[start_seconds,end_seconds],...]. Runner supplies elapsed seconds including
process/model startup. Metadata requires kind native/external/synthetic, name and SHA-256
of binary, model and config. Predictions pin canonical manifest digest and exact case IDs.
Metadata is a supplied declaration; runner verifies adapter binary, while the adapter must
verify/load the exact declared model/config. Provision and audit local adapters before use;
the executable inherits host privileges, and this runner does not sandbox network access.
No model/adapter is downloaded or implicitly selected. Existing native Moonshine host
runtime can be wrapped with this protocol; missing native VAD/command wiring stays open.

Scoring reports micro WER/CER after NFKC/casefold/alphanumeric normalization, confusion counts,
command accuracy, 20ms midpoint VAD counts/F1/miss/false-positive rates and desktop RTF.
RTF includes adapter process startup and is not device latency. Noise-only VAD miss rate/F1
remain null when undefined. Public speech corpora without endpoint annotations must not be
used to fabricate VAD truth; annotate a reviewed local held-out set for positive VAD tests.
Synthetic adapters cannot establish public-corpus results. No transcript/path/speaker is
included in reports. All six physical gates are always NOT_RUN.

VC-DATA-04: `noise.py mix --clean <speech manifest> --noise <MUSAN noise manifest>
--output <new local directory> --snr 20 10 0 --seed 0` produces deterministic file/offset
choices, looped noise, RMS-scaled SNR and joint gain reduction to avoid clipping. Requested
and quantized achieved SNR (within 0.5dB), gain, hashes and both parent manifest digests are
recorded. Silent inputs cannot define SNR and are rejected. No noise/music is treated as an
annotated positive VAD corpus. Mixed clips retain clean reference and held-out split.

`noise.py compare --baseline <reviewed report.json> --current <report.json>
--tolerances <local policy.json> --output <regression.json>` exits 2 on regression.
Policy is explicit absolute tolerances, e.g. `{"wer":0.02,"command_accuracy":0.02}`.
Baseline/current must share frozen manifest, scoring/normalization and adapter config.
Recomputed global and every slice metric catch regressions hidden by averages. Null/missing
metrics or NOT_RUN reports fail closed. Tolerances are reviewed engineering policies, not
physical acceptance thresholds. Baselines remain local and require a deliberate review;
CI does not create a real-corpus baseline from synthetic speech.

VC-DATA-05: `reporting.py --report <local report.json> --output <local report directory>`
exports summary.json and summary.html with escaped content, no scripts/external resources,
only metrics/provenance/slices and truthful physical gates. Per-case data is omitted.
`smoke.py --output <temporary directory>` verifies mixing/scoring/regression/JSON/HTML with
a generated tone and fixed synthetic transcript. It performs no recognition and never
establishes dataset accuracy. GitHub Actions executes normal/optimized Python tests,
compilation, registry validation and this smoke. Only allowlisted synthetic aggregate reports are uploaded as a seven-day CI artifact;
no corpus/transcript/credentials are cached or uploaded. Workflow uses read-only permissions,
a pinned checkout action, existing hosted Python and the public-repository cost guard.
No dependency installation or dataset/model download is performed by CI.

Local execution helpers (VC-DATA-03 integration verified with VC-DATA-05):
`extract_subset.py --archive <approved archive> --receipt <receipt.json> --output <new local
subset> --limit 100 --seed 0` rechecks SHA/size, rejects links/traversal/oversized files,
validates the full archive before writing and extracts only selected official-test clips plus
licenses/metadata. Speech Commands LICENSE must name Attribution 4.0 International.
MUSAN extraction selects only noise; root is `<subset>/musan`. Never extract unverified
archives with extractall. Generated receipts and extracted samples remain ignored.

`native_asr_adapter.py` wraps the existing local macOS Moonshine host executable, checking
vendor archive/extracted libraries and every model file against existing asr-runtime
provenance before each run. `EILO_DATA_ASR_CONFIG` points to a local JSON containing executable,
executable_sha256, cache, provenance, provenance_sha256 and model_sha256 (canonical digest
of provenance.model). Metadata binary hash pins this adapter script; config hash pins this
JSON, and model hash pins provenance.model. Command labels are exact normalized ASR words
with unknown fallback: this is an ASR-derived command baseline, not Eilo command controller
or wake-word acceptance. Native VAD remains unavailable and is reported NOT_RUN.

Command reports also expose per-reference-label accuracy, balanced accuracy over observed
labels, target-word count and target-only accuracy. Missing labels are not assigned invented
scores. Always inspect sample counts and unknown-class imbalance before interpreting accuracy.
