# VC-DATA-08 — local human VAD annotation prerequisite

The file-only VAD implementation in PR60 is reviewed/merged and its Android, JavaScript,
iOS/history and synthetic checks all passed. PR59 has the same passing checks. Both task PRs
were merged to their dependency branches after PR58 merged to main; this sprint integrates
that exact reviewed code from the dependency tip, plus this independently committed task.
Main is not merged automatically. Stable existing backlog IDs and original edits are preserved.

This task prepares local, blind listening packs for the 72 frozen clips and strict annotation
import. No annotations are fabricated. Packs omit transcript/speaker/category/model labels;
all rows begin UNREVIEWED. Explicit no-speech review is required. Incomplete or uncertain
reviews cannot become scored evidence. Model-derived labels cannot satisfy the declared method.
Record source manifest and per-case PCM hashes/sample counts, reviewer pseudonym, listening
declaration and timezone-aware review date. Integer endpoints must be sorted, disjoint and
inside the actual clip. A derived VAD-only manifest preserves receipts and component licensing.
The runner verifies the bound review before native inference and scoring; a status marker alone
is insufficient. Consistency hashes cannot authenticate a person or prove listening/label quality.

Local-only HTML packs contain audio; they are never committed, uploaded as CI artifacts or
hosted externally. Keep the generated notices and original archive licenses. The UI has a
hashed inline script and no network resources, supports draft export and local file/pasted-JSON
resume, and clears confirmations after label edits. Browser automation of file-input loading
was unavailable without expanding extension file-URL permission; no setting was changed.
Chrome draft export, pasted resume, incomplete-review and out-of-bounds guards were verified.

Validation: 49 synthetic unit tests pass under normal and optimized Python, including exact
source/PCM binding, missing/duplicate cases, draft/model/uncertain labels, invalid/future dates,
boolean/fractional/nonfinite/out-of-bounds/overlapping endpoints, changed review hashes,
status-marker spoofing, pack privacy, script hashes, unknown-field rejection and no-overwrite. Compile/registry/JS syntax
and synthetic report smoke pass. A real browser-exported MUSAN draft remains DRAFT/UNREVIEWED
and its attempted CLI import is correctly rejected without creating a result. This is not a
real human VAD annotation or quality result. No app code changed, so local mobile rebuilds
are not applicable to this desktop-only tool; hosted foundation checks remain required.

Next: an acoustic reviewer listens and labels the packs, then reviews those annotations.
Only then import them and run the pinned VAD adapter for actual corpus F1/miss/false-positive
metrics. Physical gates stay NOT_RUN, production NOT_ENABLED, S08 feasibility on hold. Native
mobile voice/session/trust/offline-voice wiring and locked/device trials remain outside this
completed annotation-tooling checkpoint.
