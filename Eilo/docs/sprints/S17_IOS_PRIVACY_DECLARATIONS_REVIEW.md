# S17 dependency — actual iOS declaration reasons and import candidates

The exact previously recorded normal unsigned simulator Release app was reinspected without
rebuilding or launching it. All eight manifests and four native binaries match the canonical
inventory tree and individual hashes. The new `packages/ios-privacy-audit` snapshot records three
category/reason pairs (FileTimestamp/C617.1, SystemBootTime/35F9.1, UserDefaults/CA92.1), explicit
absent fields and seven selected undefined imports across Eilo/React/ReactNativeDependencies.
Hermes has no match in the selected list. Each matched category appears in an app-wide declaration;
this does not establish SDK ownership, complete coverage, executed APIs or purpose suitability.

Apple's current category/reason and TN3183 documentation was reviewed as context; primary links
and the bounded method are in the package README. No reasons were added/removed from the app.
The checker validates syntactic declarations and recorded provenance, not Apple eligibility or
compliance. Required follow-up includes actual call-purpose/data-flow review, SDK ownership,
complete API/manifest coverage and the final signed device archive. Empty collected-data and
false tracking declarations are not evidence of runtime data handling or no network traffic.

Sixteen regressions cover duplicate XML/binary keys, entity denial, malformed/duplicate reasons,
unknown versus empty fields, private-value suppression, exact symbol filtering, artifact/tool
changes during collection, wrong artifact rejection, stale pins, acceptance promotion and report
overwrite. Both Python modes and all offline VC-DATA workflow steps must pass. CI validates
recorded evidence without the app/tool and uploads only the two summaries, retained seven days.

No app source, lockfile, old inventory, dependency cache, phone, microphone, signing, credentials,
download, installation, launch or distribution was changed/accessed. Personal edits are preserved.
This is a concrete VC-VERIFY-07/11 evidence increment, not full task/sprint acceptance. Physical
gates stay OPEN, S08/release HOLD, memory disabled, network/privacy NOT_ESTABLISHED; license,
full SBOM, purpose suitability and final device/archive acceptance remain unresolved.
