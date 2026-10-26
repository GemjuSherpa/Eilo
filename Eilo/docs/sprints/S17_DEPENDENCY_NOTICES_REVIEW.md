# S17 dependency — cached notice and parent-declaration provenance

The normal-build inventory's two third-party declaration gaps now have local source evidence:
`exit:0.1.2` declares MIT in a legacy licenses array and supplies a notice in its SHA512-SRI-matched
cached npm tarball, with installed package.json/notice byte matches; `listenablefuture:1.0` has an
embedded child POM identical to its pinned cache POM, with a literal link to cached guava-parent
26.0-android, whose metadata declares Apache Software License 2.0. These are observed source and
metadata facts, not a new legal interpretation or permission to redistribute the complete app.
Historical inventory/lock declarations remain unchanged; no license is selected for Eilo.

The collector also verifies/scans all 100 Maven artifacts with recorded hashes. Twelve have
matching notice files, with two distinct notice byte hashes. Both hashes occur in the exact
recorded APK's two matching notice files. Eight Maven entries lack artifact digests and stay
unscanned; 88 scanned artifacts have no matching embedded notice filename. The exact unsigned
simulator app has no matching notice filenames. Missing filenames do not establish unlicensed
code or a failure; equal notice bytes do not establish complete attribution. Full native/prebuilt,
source, iOS and transitive notice/redistribution review remains necessary.

`packages/dependency-notices` contains the bounded read-only collector, actual observed hashes/
declarations, strict JSON/HTML report validator and regressions. It rejects archive traversal,
links/duplicates, mismatched cache/SRI/installed/artifact bytes, unverified embedded child POMs,
unsafe coordinates, XML entities, ambiguous JSON and parent cycles. Missing parent cache data
stays unresolved without fetching. Source and prior build-inventory pins remain traceable. No
inspected code or package lifecycle script is executed, and nothing is extracted to disk.

Only relative public member paths, hashes, coordinates and declarations are exported. Full notices,
binaries, raw logs, user paths and credentials remain out of repository/artifacts. CI revalidates
snapshots/contracts without caches or downloads; it does not authenticate publisher/cache content
or attest the original normal builds. Existing normal app binaries and inventory are unchanged;
no new app compile, installation, launch, physical device, download or account access occurred.

The four local Eilo workspaces still await the owner's licensing decision. This inventory subtask
does not close VC-VERIFY-07/11, full SBOM, signing or redistribution review. S08/release remains
HOLD, memory disabled, physical gates OPEN and network/privacy NOT_ESTABLISHED. No production
runtime or confidence policy is activated.
