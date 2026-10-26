# Pinned iOS privacy declaration audit

This S17 VC-VERIFY-07/11 evidence increment reads the exact normal unsigned simulator Release
app previously inventoried by `build-inventory`. It adds declared reason codes, explicit missing
versus empty fields, and selected undefined-import candidates. It does not modify app manifests,
choose new reasons, build/launch/install an app, inspect a device or contact a service.

## Actual observations, 26 October 2026

Eight hashed manifests and four hashed native binaries match the prior canonical app-tree digest.
The manifests declare three distinct category/reason pairs: FileTimestamp/C617.1,
SystemBootTime/35F9.1 and UserDefaults/CA92.1. All eight declare tracking false and an empty
collected-data list; tracking-domain fields are absent. These are declarations, not measurements.

The existing Xcode `nm -u -j` tool finds seven selected imports: Eilo imports `fstat`; React imports
`fstat`, `stat`, `mach_absolute_time` and the NSUserDefaults class; ReactNativeDependencies imports
`fstat` and `stat`; Hermes has no match in this deliberately limited list. Every matched category
has an app-wide declaration. This is not an ownership mapping between an SDK's code and its
manifest. An import need not execute, reveal its purpose or identify which source call is used.
No match does not establish absence: Swift/Objective-C dispatch, wrappers, inlining, stripped
symbols and unlisted APIs are outside this method. No DiskSpace candidate matched the selected
four-symbol subset; this does not establish that disk-space APIs are unused.

Apple's [required-reason API documentation](https://developer.apple.com/documentation/bundleresources/app-privacy-configuration/nsprivacyaccessedapitypes/nsprivacyaccessedapitype)
was checked on 26 October 2026. In brief, C617.1 concerns file metadata in app/group/CloudKit
containers; 35F9.1 concerns elapsed app-event timing and timers, with restrictions on transmitting
derived information; CA92.1 concerns defaults accessible to the app itself. Those descriptions are
review context, not a finding that every actual call meets them. The parser checks code syntax,
not current Apple reason eligibility. Before distribution, trace actual call purposes and data
flows, review every SDK's ownership and full required-reason/API coverage, then inspect the final
signed device archive and current Apple rules. Reusing these simulator facts is insufficient.
See also [Apple TN3183](https://developer.apple.com/documentation/technotes/tn3183-adding-required-reason-api-entries-to-your-privacy-manifest).

## Reproduce from the same local artifact

From Eilo, using only the existing app and Xcode tool:

```sh
python3 packages/ios-privacy-audit/audit.py --ios-app /explicit/recorded/Eilo.app \
  --nm /explicit/existing/Xcode/toolchain/usr/bin/nm --output /new/observed.json
python3 -m unittest discover -s packages/ios-privacy-audit -p 'test_*.py' -v
python3 -O -m unittest discover -s packages/ios-privacy-audit -p 'test_*.py' -v
python3 packages/ios-privacy-audit/report.py --output /new/report
```

Collector and prior inventory source hashes are pinned. The complete app tree, manifest/binary
bytes and tool hash are checked before/after inspection. Wrong artifacts, symlinks, oversized
inputs, duplicate XML/binary-plist keys, external entity declarations, malformed/duplicate reason
entries and failed tools stop collection. The standard Apple plist doctype is allowed without
network resolution. Absent declarations remain unknown; domain values and collected-data details
are not exported. Unknown manifest keys stop this bounded parser for review rather than being
silently dropped. Nothing is executed from the inspected app or extracted to disk.

CI validates the recorded contract, source pins and sixteen synthetic regressions in both Python
modes. It cannot reproduce or authenticate the original binaries/tool run. Only JSON/HTML
summaries are uploaded, for seven days; no binaries, full manifests, logs, domains or private paths.
The exporter refuses overwrite. Changes to relevant inventory sources require fresh inspection,
not blind pin updates. No new compile is needed for this read-only audit; ordinary native build
checks still gate the PR. Physical tests remain OPEN, release/S08 HOLD, persistent memory disabled,
network privacy and App Store acceptance NOT_ESTABLISHED, purpose review REQUIRED.
