# Pending integrated requirement closure

`ledger.json` maps all 93 requirement IDs explicitly present in `planning/sprint-issues.json` to their exact planned task IDs. IDs are traceability labels; the issue source does not include the complete original requirement prose. Do not invent missing requirement definitions or treat this derived registry as a new specification. Historical task checkboxes/PR merges are not current integrated acceptance.

The ledger pins ten supporting document/planning records by SHA256. Every requirement has an explicit blocker and context references. It intentionally permits only BLOCKED full-app statuses, HOLD release/S08, no supported configurations and disabled persistent memory. A future accepted-evidence format requires a reviewed change with real full-app evidence, not toggling a flag. The checker verifies structure, coverage, planner/task mapping and hashes; it cannot prove observation truth, inspect binaries/phones/stores/traffic or decide acceptance.

From `Eilo`:

```
python3 -m unittest discover -s packages/release-evidence -p 'test_*.py'
python3 -O -m unittest discover -s packages/release-evidence -p 'test_*.py'
python3 packages/release-evidence/closure.py
```

A valid pending ledger exits 0 so CI can verify preparation truthfully. `--require-release-ready` always exits 2 on this pending-only format. Invalid/missing/stale data exits 1 and prints only a fixed classification, never raw evidence/error content or source paths. Source paths are local repository files, bounded, checksum-pinned and cannot traverse or use symlinks. Sources are supporting context, not physical acceptance.

When a pinned record changes, review its new claims and affected requirement links before deliberately refreshing its checksum. Never update a digest solely to make a stale check pass. Newly planned requirements/task assignments must be reconciled too. No recordings, conversation text, packet files, endpoints, credentials, device serials or personal logs belong in the ledger. See S17_PRIVACY_AUDIT.md and S17_RELEASE_PREPARATION.md for prerequisites and the actual remaining work.
