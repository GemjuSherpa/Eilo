# Cached dependency notice provenance

This S17 follow-up traces source evidence for gaps in the normal-build inventory, using only
existing approved local caches and the exact artifacts already recorded in `../build-inventory`.
No downloads, package installation, app build/change/activation, device access, license selection,
signing or distribution. Historical inventory observations remain unchanged.

## Actual observations

- All 100 Maven JAR/AAR artifacts with an AGP-recorded digest were matched by SHA256 and scanned
  for bounded notice filenames at the root and one `classes.jar` layer. Twelve artifacts contain
  twelve matching notice files, representing two distinct byte hashes. Both distinct byte hashes
  are present in the recorded Android APK. Eight digest-less Maven metadata entries are explicitly
  unscanned; 88 scanned artifacts have no matching embedded notice filename. That absence does
  not establish absence of a license or missing compliance; notices can be supplied elsewhere.
- `com.google.guava:listenablefuture:1.0` has no direct license declaration in its cached POM.
  Its verified JAR's embedded POM matches the cached child POM byte-for-byte. The literal parent
  link identifies cached `com.google.guava:guava-parent:26.0-android`, whose metadata declares
  “The Apache Software License, Version 2.0.” Both POM hashes and declarations are recorded.
  This is cached declaration provenance, not authenticated publisher metadata or a full Maven
  effective-model/redistribution determination. No properties, relative paths, BOMs or remote
  resolution are inferred; cycles, unknown cache inputs and depth beyond four fail or stay open.
- `exit@0.1.2` has no npm-lock license field, but its lock-SRI-verified cached tarball declares
  MIT in its legacy `licenses` array and contains `LICENSE-MIT`. The package.json and notice
  match the installed package bytes. The source archive, files, lock integrity and declaration
  are pinned. No installed vendor files or root/package license declarations are modified.
- The same APK has two matching notice files; the same unsigned simulator app has no matching
  notice filenames. Both artifact fingerprints match the preceding inventory. Matching filenames
  and bytes do not establish complete attribution, detect every embedded notice or determine legal
  compliance. No iOS device archive, runtime traffic, storage or physical pass is inferred.

The four Eilo workspaces still require the owner's license decision. This package does not
choose a license, issue legal approval, or change the five missing fields in the historical npm
lock snapshot. It supplies evidence explaining two third-party metadata gaps without erasing
those original observations. Full shipped-component mapping, native/prebuilt/source notices,
iOS attribution, redistribution review and signed-build provenance remain open.

## Collector boundaries

`notices.py` requires explicit `--gradle-cache`, `--npm-cache`, `--node-modules`, `--apk`,
`--ios-app` and new `--output` paths. It first validates/pins the committed build inventory and
lockfile, then verifies cache bytes. No package scripts or inspected code are executed. ZIP and
tar entries are bounded, relative, unique and free of links/devices; there is no extraction to
disk. Only small notice/POM/package metadata members and one bounded nested classes.jar are read.
Cache coordinates must be literal and remain inside the chosen root. XML DTD/entities and
ambiguous/nonfinite JSON are rejected. Missing parents remain explicitly unresolved; no download
fallback exists. Source pins are checked before and after collection.

Archive bytes for `exit` must match the committed SHA512 SRI before parsing, and both installed
file hashes must match the archive. Maven notice scans require the artifact digest recorded in
the existing inventory and recheck it after reading. Parent provenance additionally requires a
pinned cached child POM identical to the verified child JAR's embedded POM. Parent POM hashes
are locally observed, not publisher-signature validation. Canonical app-tree/APK hashes bind
packaged notice checks to the prior artifacts; no new compile or installation is needed.

Reports retain only relative public member paths, hashes/sizes, declared license names/URLs,
coordinates, statuses and artifact identities. No raw license text, binaries, source packages,
logs, absolute user paths, credentials, provisioning identities, audio or personal data are
committed/uploaded. Standard third-party notices remain in their original approved caches.

## Reproduce without downloads

Use existing normal-build APK/simulator app and cache roots from `../build-inventory/README.md`.
The npm cache root is the existing `_cacache` directory and the node-modules root is the existing
installed tree; neither is changed. Output must be new. The collector is a local-only inspector.

From Eilo, validate without caches or artifacts:

```sh
python3 -m unittest discover -s packages/dependency-notices -p 'test_*.py' -v
python3 -O -m unittest discover -s packages/dependency-notices -p 'test_*.py' -v
python3 packages/dependency-notices/notice_report.py --output /new/notice-report
```

The exporter validates closed schemas, baseline/source/lock pins, complete component coverage,
parent-child evidence and unchanged acceptance gates; it refuses overwrite. CI checks the
recorded evidence/schema and synthetic regressions, not the truth of local observations or
cache/publisher authenticity. It uploads only JSON/HTML summaries with seven-day retention.

S08/release HOLD, persistent memory disabled, physical gates OPEN, SBOM completeness and
network/privacy NOT_ESTABLISHED, redistribution review REQUIRED and Eilo licensing decision
OWNER_DECISION_PENDING remain unchanged.
