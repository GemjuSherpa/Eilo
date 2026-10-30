# S05 isolated iOS source score diagnostic

The iOS prebuilt ASR API exposes no reviewed calibrated confidence. This increment
ports the existing isolated source score diagnostic to the simulator using only
approved caches and the installed toolchain. It changes no ordinary runtime,
shipping C ABI, model, confidence policy or existing Android report.

The final collection links the approved Moonshine simulator archive's isolated
prelinked runtime member (observed ORT 1.23.2) with the verified source overlay.
Six synthetic fixtures produce 35 diagnostic paths and one NOT_EXERCISED full-draft
path. The name fixture's intended full draft instead accepted three of nine rows
and redecoded; no scores are reported under that absent path. Strict actual-row
oracle/token equality checks, divergence checks and partial-score cleanup remain
active. All other planned path types are exercised on each fixture, and full
accepted drafts on the other five. All 54 deliberate faults and four invalid inputs
reject usable scores. This is partial coverage, not a complete matrix pass.

Initial ORT1.28.2 branch failure, aggregate counter diagnosis, unsuccessful bounded
full-draft construction and matching-version vendor-runtime diagnosis remain in
history/local logs. The fixture mismatch is not silently promoted or removed.
Step/batch differences remain unqualified, with cause NOT_ESTABLISHED.

Darwin double and long double both have 53 mantissa bits. Real-row comparison is
explicitly same precision. A separate actual iOS helper binary checks eight small
synthetic rows across three source path tags against an independent Python
Decimal80 calculation; 24 checks and six invalid guards pass, with maximum
absolute/relative errors about 3.60e-17/1.32e-16. This does not establish an
extended-precision oracle for every model row or confidence calibration.

Validation includes actual simulator source execution and independent math controls,
normal/optimized package tests, all offline VC workflow blocks and secret scans.
CI validates closed aggregate evidence and keeps missing paths/unknowns explicit;
only redacted JSON/HTML summaries are uploaded for seven days. The relocated native
probe requires no custom dynamic dependency/RPATH. Source/model/archive/fixture
hashes are verified before/after, with no new dependency installation/download,
microphone, speaker, LLM, physical device or developer signing credential.

Calibration NOT_ESTABLISHED, threshold NOT_GRANTED, cross-platform calibration
transfer NOT_AUTHORIZED, ordinary runtime NOT_REPLACED, physical OPEN/NOT_RUN,
S08/release HOLD and persistent memory DISABLED remain unchanged. Shipping
source/caller/trust/licensing, calibrated confidence and device acceptance stay open.
