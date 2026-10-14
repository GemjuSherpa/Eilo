# Public corpus evaluation — VC-DATA-01–05

Offline desktop tools, separate from Eilo's mobile production pipeline. All three initial
corpora have user-approved local inputs: Speech Commands0.02, MUSAN SLR17 and the MDC-curated
Common Voice26 Australian English validated subset. No automatic downloader, account login,
model provisioning or cloud inference is added. Audio, TSVs/transcripts, receipts, normalized
clips and detailed results belong under `Eilo/.local/datasets/` (ignored), never Git or CI uploads.
All physical capture/interruption/endurance/standby/screen-off/device-latency gates remain
NOT_RUN; production readiness stays NOT_ENABLED. See `../../docs/dataset-evaluation/REVIEW.md`.

## Licensing and integrity — VC-DATA-01

`registry.json` records exact versions, public source/terms URLs, permissions and checksum
scope. User approved public downloads and subsequently the selected CV dataset/MDC terms
on14October2026. CV is CC0-1.0; its platform terms forbid speaker identification and rehosting.
Its archive is a curated accent subset, not the full English release. Safari decompressed the
download; the pinned SHA/size covers the resulting TAR, not the unavailable original gzip.
Speech Commands' archive LICENSE is CC BY4.0; its SHA/size match TensorFlow's immutable published
checksum source. MUSAN's compilation is CC BY4.0, while component licenses differ. Initial
selection is restricted to `noise/free-sound`, whose embedded inventory declares recordings
Public Domain. Inventory hashes and corpus attribution remain local; other components need review.

From this directory:

```sh
python3 manifests.py
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -v
python3 manifests.py --dataset musan --archive ../../.local/datasets/musan.tar.gz \
  --license-evidence ../../.local/datasets/musan-license-review/musan/noise/free-sound/LICENSE \
  --output ../../.local/datasets/new-musan-receipt.json
```

Receipts stream SHA-256 and record size/license-evidence hash. Pinned registry mismatch fails;
LOCAL_OBSERVED proves repeatability, not publisher authenticity. CV license evidence is a
local observed-card/user-approval summary linked to the public terms, not a copy of raw legal
text or credentials. No signed URLs or account secrets are recorded.

## Preprocessing and extraction — VC-DATA-02

```sh
python3 extract_subset.py --archive <approved archive> --receipt <receipt.json> \
  --output <new ignored subset> --limit 100 --seed 0
python3 preprocess.py --dataset speech_commands --root <subset> --receipt <receipt.json> \
  --output <new ignored frozen directory> --split test --limit 100 --seed 0
```

Extraction rechecks SHA/size, validates the full archive before writing, rejects links/devices,
traversal/oversized/duplicate members and extracts only selected official-test clips plus
license/metadata files. TAR/gzip streams are supported; no extractall or archive permissions.
CV train/dev/test anonymous speaker IDs must be disjoint before extraction. This verifies the
curator's split, not an opaque vendor model's training history. MUSAN root is `<subset>/musan`.

Seeded SHA-256 ordering fixes selection. Source/normalized WAV/PCM hashes freeze inputs;
IDs anonymize file/speaker names. Speech Commands official testing/validation lists and
CV test/dev TSVs determine evaluation membership. Train is rejected; no random new split.
PCM WAV8/16/24/32-bit mono/stereo converts to16kHz mono PCM16. Integer area averaging downsample
and linear interpolation upsample are a reproducible desktop baseline, not production SRC.
No gain normalization, speech trimming, padding or transcript-changing crop. MUSAN noise
uses first30s. Failed/incomplete outputs have no usable manifest; choose a new output directory.

CV MP3 needs an explicitly hash-pinned installed decoder. `--decoder-kind ffmpeg` uses local
file-only, single-threaded bitexact PCM conversion and rejects duration-limit clips. On macOS,
`--decoder-kind afconvert --decoder /usr/bin/afconvert --decoder-sha256 <observed hash>` uses
Apple's existing converter: PCM16/16kHz/mono downmix, SRC quality127/norm. Binary hash, platform
and output hashes are recorded.30s-or-longer/oversized decoded output is rejected. Restricted
execution may need existing OS codec-service access; no decoder installation is required.
Frozen PCM, rather than redecoding on another OS, is the regression input. Decoder/OS changes
require a newly reviewed manifest. Detailed metadata stays local.

## ASR/VAD/command benchmarks — VC-DATA-03

```sh
python3 benchmark.py --manifest <frozen/manifest.json> --output <local/report.json>
python3 benchmark.py --manifest <frozen/manifest.json> --adapter <local executable> \
  --adapter-metadata <local metadata.json> --output <local/report.json>
```

No adapter yields NOT_RUN. `--predictions <local predictions.json>` scores saved outputs instead.
Predictions must pin canonical manifest digest and exact case IDs; missing/extra/duplicate/NaN
outputs fail. Metadata requires kind native/external/synthetic, name and binary/model/config
SHA-256. Synthetic adapters cannot establish public-corpus results. Supplied metadata is a
declaration: runner verifies adapter binary; adapter must verify its model/config. Local
executables inherit host privileges; this runner does not provide a network sandbox.

Adapter contract: executable receives request.json and response.json paths. Request contains
schema_version1, id, task, absolute normalized WAV path and rate16000; never truth labels.
Response has id, transcript for ASR; commands also has command (ten targets, unknown or silence);
VAD uses sorted nonoverlapping [[start_seconds,end_seconds],...]. Runner records whole process
elapsed time, including initialization/integrity work. Output is bounded and timeout controlled.

`native_asr_adapter.py` wraps the already-provisioned macOS Moonshine host executable. Set
EILO_DATA_ASR_CONFIG to local JSON: executable, executable_sha256, cache, provenance,
provenance_sha256 and model_sha256 (canonical digest of provenance.model). Wrapper verifies
vendor archive/extracted files, every model file, runner-pinned config and model manifest.
Metadata binary hash pins this wrapper; config hash pins raw JSON. Command labels are exact
normalized ASR words with unknown fallback, an ASR-derived baseline rather than Eilo's command
controller/wake-word acceptance. No native VAD/model is downloaded or implicitly selected.

Scoring: micro WER/CER after NFKC/casefold/alphanumeric normalization, command confusion,
overall/per-label/balanced/target-only accuracy, result slices and desktop RTF. VAD counts use
20ms actual frame midpoints (including partial final frame), F1/miss/false-positive rates;
undefined values remain null. Native VAD and reviewed endpoint annotations remain absent.
MUSAN category labels are CORPUS_CATEGORY_WEAK_LABEL, not frame truth. Real VAD scoring requires
actual reviewed time-aligned annotations marked REVIEWED_TIME_ALIGNED. No VAD acceptance is
inferred from noise categories or utterance transcripts. RTF is not physical device latency.
Reports omit transcripts, audio paths and speaker IDs. Source quality/annotation declarations
still require review; a validator cannot certify their truth.

## Noise/regression — VC-DATA-04

```sh
python3 noise.py mix --clean <speech manifest> --noise <MUSAN noise manifest> \
  --output <new ignored directory> --snr 20 10 0 --seed 0
python3 noise.py compare --baseline <reviewed report> --current <report> \
  --tolerances <policy.json> --output <regression.json>
```

Deterministic file/offset selection, looped noise, RMS SNR and joint headroom avoid clipping.
Target/achieved SNR(within0.5dB), gains, hashes and both parent manifest digests are recorded.
Silent inputs cannot define SNR and fail. Mixed speech retains reference/split. Noise audio
mixing does not require fabricated VAD annotations. All embedded licenses/attribution remain
local; only reviewed Free Sound recordings are selected by default.

Comparison requires the same frozen manifest, scoring/normalization and adapter config and
recomputes global/every-slice metrics. Missing/null metrics or NOT_RUN baselines fail closed;
regression exits2. Explicit absolute policy example:`{"wer":0.02,"command_target_accuracy":0.02}`.
Tolerances are reviewable engineering policy, not physical acceptance thresholds. Clean and
noisy manifests are different and must not be presented as the same regression baseline.
No real-corpus baseline is automatically approved by a synthetic self-comparison.

## JSON/HTML and CI — VC-DATA-05

```sh
python3 reporting.py --report <local report.json> --output <local summary directory>
python3 smoke.py --output <temporary directory>
```

Exporter allowlists aggregate/provenance/slice fields and escapes HTML; no scripts/external
resources or per-case data. Synthetic smoke generates a tone with fixed synthetic transcript
and checks mixing/scoring/regression/JSON/HTML; it performs no recognition. Read-only public
GitHub Actions run normal/optimized tests, compile/registry checks and smoke without models,
corpora, microphone or dependency installation. Only allowlisted synthetic summaries are
uploaded with seven-day retention using pinned official actions. No real audio/transcript,
credentials or corpora are cached/uploaded. Full hosted foundation checks remain separate.

### Locked diagnostic regression candidates (VC-DATA-06)

`baseline.py candidate --manifest PATH --baseline REPORT --tolerances POLICY --output LOCK`
creates a content-addressed candidate for PR review. `baseline.py check --manifest PATH
--baseline REPORT --lock LOCK --current REPORT --output RESULT` verifies the same corpus,
case identities, reference counts, durations, baseline report and tolerance policy before
comparing every slice. Existing output evidence is never overwritten. Exit 2 indicates a
regression. Locks detect content changes; they are not signatures or proof of reviewer approval.
Keep full manifests and case reports locally; publish only aggregate summaries and digests.

Review the proposed tolerance policy with the task PR. A comparison PASS means repeatability
within this frozen diagnostic suite; it does not establish product quality, corpus coverage,
physical-device feasibility or approval of a release. No automatic acceptance mechanism is added.
Historical v1 reports must not be silently relabelled: the checked-in continuation evidence
records an explicit ASR/command-only compatibility mapping for the v2 partial-VAD-frame fix.
VAD comparisons require fresh v2 scoring.

### Native file-only VAD (VC-DATA-07)

`native_vad_adapter.py` implements the existing request/response contract with the pinned
sherpa-onnx 1.13.8 C API via Python ctypes. It uses the approved local Silero v5 model,
CPU/one thread/16 kHz, threshold 0.5, minimum speech 160 ms and silence 500 ms. Inputs are
bounded to 30 seconds. Each clip gets a fresh detector, 512-sample windows, zero padding of
the final window, explicit flush, clamping to the original duration, reset and destruction.
Native returned segments are freed after consumption. No microphone, application or download
is activated by this adapter. Model/runtime/license provenance is in vad-provenance.json.

Set `EILO_DATA_VAD_CONFIG` to a local JSON with `runtime_version`, `settings` (exact SETTINGS
from the adapter), `library`, `runtime_files` (path/sha256 entries), and `model` (path/sha256).
Use the normal benchmark runner and adapter metadata to score reviewed annotations. The config
and model hashes must match EILO_DATA_ADAPTER_CONFIG_SHA256 and EILO_DATA_ADAPTER_MODEL_SHA256;
the runner supplies those variables from its metadata. The wrapper, config, model and runtime
are all pinned. Do not edit source or pins to accommodate a different ABI without review.

Without reviewed annotations, use `vad_diagnostics.py --manifest PATH --config CONFIG --output
RESULT` with the same expected config/model hash variables. It verifies the corpus and emits
aggregate execution/detected-duration counts labelled EXECUTED_UNSCORED. It cannot produce F1,
miss rate or false-positive rate. The scoring runner still rejects weak public VAD labels.
