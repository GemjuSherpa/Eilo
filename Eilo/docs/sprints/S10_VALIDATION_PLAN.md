# S10 — encrypted-store validation plan (not executed)

This plan is independent preparation. VC-GATE-04 remains HOLD_PENDING_PHYSICAL_EVIDENCE and
persistent_memory_allowed=false. No SQLCipher package, store, schema, persistence adapter or
migration may be implemented under this preflight. Every experiment below remains NOT_RUN.
S09 merge approval accepts its reviewed scope, not its unrun physical/security evidence.

## Entry and dependency selection

Before VC-STORE-01, review VC-GATE-04's actual experiment-linked human decision and the native
VC-KEY-03 policy/driver evidence. A merged document or successful synthetic test is insufficient.
Then select and pin exact native SQLCipher sources/artifacts, hashes, crypto provider, license,
OS/ABI/build configuration and wrapper API. Inspect effective linkage to reject a system SQLite
fallback. This preflight selects no library/version and installs nothing. Native key material,
SQL query bindings, private text and errors must stay outside JS/logs/CI artifacts.

The current direct mobile dependency manifests inspected for readiness do not declare SQLCipher.
That is an inventory of those files, not a claim about every cache or installed executable.
Real test results must identify the exact loaded library and crypto provider. Check runtime
cipher_version and the chosen build's settings, then prove an actual keyed schema read. A
successful key-setting call alone is not proof of a correct key or encrypted database.

## Future task experiments

| Stable task | Required experiment and preserved failure evidence |
| --- | --- |
| VC-STORE-01 | With approved exact library, create synthetic markers through a native authenticated connection. Force database, WAL, rollback/statement journals and temporary-workload paths. Inspect files while transactions are live and after crash/restart. Wrong/missing keys and plain SQLite must fail a real schema/query read. Correct key and integrity checks must pass. Preserve effective temp-store/build settings and absence of plaintext markers; inspect metadata independently. |
| VC-STORE-02 | Commit one finalized user/reply transaction with source/session IDs and expiry, then restart. Abort before commit, revoke auth between preparation/commit, and enter private mode: no content row may survive. Retry the same operation identity without duplicating records. Failed writes report failure and retain prior committed data. |
| VC-STORE-07 | Account exact bytes for DB, indexes, live journals/WAL, future inbox and maintenance/write reservations; exclude generic model assets. Exercise 199999999/200000000/250000000-byte boundaries using bounded fixtures, not real large files. Reject escaping paths/symlinks and double-counting aliases. Reconcile accounting after restart, concurrent reservations and failed cleanup. |
| VC-STORE-03 | Interrupt before emission, mid-clause, after submission and after verified completion. Persist truthful progress/interruption metadata; queued/submitted speech does not prove hearing. Roll back a failed turn transaction and preserve the original playback ledger's distinctions. |
| VC-STORE-04 | Seed beyond page size with equal timestamps, expired/deleted/private rows and concurrent deletion. Validate bounded deterministic pagination without duplicate/omitted eligible rows. Revoke/expire auth between queued read and native publication: no old private page reaches a sink. |
| VC-STORE-05 | Test exact 90-day default and selected retention boundaries, clock forward/backward changes and restart. A source already judged expired must never reappear after rollback of the wall clock. Apply expiry before every read/retrieval, not only maintenance; do not invent an approved clock policy in this plan. |
| VC-STORE-08 | Before any history-enabled turn, reserve sufficient safe capacity transactionally. Compete for the final reservation; fail on disk-full, quota, journal-growth or write error. Preserve prior history and return actionable failure; never silently switch to private mode. Release only the reservation owned by that operation after abort. |
| VC-STORE-09 | Delete one synthetic source with dependent facts/index/cache references. Force rollback at each transaction boundary, restart, and issue stale recall callbacks. Committed deletion hides the source immediately and invalidates derivatives; rollback preserves a consistent original state. Later retrieval integration is a separate dependency, not simulated acceptance. |
| VC-STORE-06 | Batch expired-source cleanup under authenticated eligible maintenance. Crash/restart and fail each batch step; retain consistent live data and resume bounded work. Test foreign-key/derived-data cleanup and disk-full. Do not promise cleanup at an exact time while the OS has stopped execution. |
| VC-STORE-10 | Authenticate an explicit screen delete-all; race pending reads/writes/imports and privacy transitions. Remove personal stores/inbox/key associations, reject every old capability, and verify old ciphertext cannot reopen with a new key. Partial failure cannot report completed deletion; new storage needs fresh approved consent. No claim of forensic flash erasure. |

## Actual encryption and filesystem evidence

Zetetic's design documents distinguish encrypted database/journal/WAL page content from other
transient files, and require disabling file-backed temporary storage for sensitive temp work.
Inspect the selected library's build settings and actual temporary-file behavior, rather than
assuming an application PRAGMA proves every native path. Its API also documents runtime version,
provider and integrity reporting. These references guide future tests; they are not results.

Keep a unique nonpersonal marker per candidate experiment and inspect all owned file paths and
open transient descriptors without publishing private data. Record format, size, keyless failure,
authenticated integrity/read results and synthetic marker findings. Investigate plaintext header,
path/size metadata, crash files and backup exclusions independently: encryption does not imply
all filesystem metadata is confidential. Never publish keys, raw contents or diagnostic errors.

Future native consumers must retain no key copies outside S09's registered ownership; close
connections before lock/expiry teardown completes. Validate session/token/context immediately
before transaction commit and before publishing any private output. A post-operation denial
cannot undo an already committed side effect. Test the actual SQLCipher consumer lifecycle,
not only the existing key/session mocks. No consumer is implemented by this plan.

## Result and review protocol

Use isolated app-private synthetic stores, exact device/OS/ABI/library identifiers and new run
IDs. Preserve original failed trials, crashes and incomplete runs. Successful compilation, mock
transactions, desktop SQLite or an encrypted filename cannot count as SQLCipher/mobile/security
acceptance. Keep real physical key-authentication and backup/transfer checks distinct from host
unit evidence. Tests must pass before task commits; changed apps require the same simulator
build/install/three ten-second launch workflow. Consolidate task branches into the S10 sprint and
open one review PR; main merging requires the user's separate authorization.

Current plan result: NOT_RUN_DEPENDENCY_BLOCKED. No S10 stable task is marked implemented/passed.

## Primary implementation references for future selection

- [SQLCipher design](https://www.zetetic.net/sqlcipher/design/)
- [SQLCipher native API and integrity settings](https://www.zetetic.net/sqlcipher/sqlcipher-api/)

The exact future version/license/build and independent security review remain unselected.
