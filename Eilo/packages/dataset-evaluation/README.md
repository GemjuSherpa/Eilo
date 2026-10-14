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
