# Normal build artifact inventory

This package inspects actual normal Android release-variant and unsigned iOS simulator Release
artifacts using existing local tools/caches. It is a dependency of S17 VC-VERIFY-07/11, not a
complete SBOM, license approval, signed device archive, network/privacy audit or release pass.
No app is installed or launched, no phone/microphone accessed, no account/credentials inspected,
no signing keys generated, no dependencies fetched and no distribution performed.

## Observed 26 October 2026

The normal Android release build, 380 unit tests and release lint passed offline. The unsigned
iOS simulator Release build succeeded after generating missing local React Native codegen
inputs; its initial failure is retained locally. Existing release framework archives were checked
present, then Pods were cloned using the filesystem's copy-on-write support before changing
configuration. Personal Pods and tracked edits were preserved. No ordinary runtime/model change.

| Evidence | Observation | Limit |
| --- | --- | --- |
| Android APK | 1,040 ZIP entries; 52 native libraries across four ABIs; observed hashes/ELF NEEDED names and manifest permissions | Normal release variant uses the existing development signing configuration; signature provenance not reviewed; not distribution approval |
| iOS app | 136 files; four native binaries; eight privacy declarations; tree/file/binary hashes and linked basenames | Unsigned simulator Release, not an ARM64 device archive or physical evidence; imports are not a complete SDK inventory |
| AGP SDK metadata | 108 Maven entries; 100 SHA256 values match cached JAR/AAR bytes; eight have no recorded digest | Co-observed AGP report, not complete class-to-binary attribution; metadata-only/unrecorded entries stay unverified |
| Maven license metadata | One component has no direct POM license declaration: com.google.guava:listenablefuture:1.0 | POM declarations are not legal approval, full notice coverage or inheritance resolution |
| npm lock | 940 non-link records; five lack a lockfile license field (four local workspaces and exit:0.1.2) | Includes development/build dependencies; neither absence of the field nor presence of a license establishes legal status or shipment |
| CocoaPods | 149 lock records including subspecs; six acknowledgement records including generated footer | Hashes preserve notice evidence, not complete transitive licensing or 149 distinct shipped libraries |
| Packaged evaluation resources | No files with .mp3/.wav/.f32/.gguf/.onnx/.ort extensions in either artifact | This is a named-extension check, not proof of no embedded content, datasets, sensitive data, logs or device stores |

Actual Android permissions include INTERNET and microphone/foreground-service/notification
permissions. Their presence is recorded, not converted into a runtime egress or capture claim.
iOS privacy declarations are reported as declarations; missing tracking declarations remain null,
not false. Endpoint lists, signing/provisioning identities and full plist bodies are not exported.

## Collector and provenance

`collect.py` requires explicit `--apk`, `--sdk-metadata`, `--gradle-cache`, `--ios-app`,
`--pods-lock`, `--acknowledgements`, `--npm-lock`, `--readelf`, `--aapt`, `--otool` and new
`--output` paths. It performs no builds, downloads, installation, signing or device access.
The known tools are the existing NDK27.1 LLVM readelf, Android build-tools37 aapt2 and effective
Xcode27.1 toolchain otool. SHA256 pins identify the tools, collector, lockfiles/build configuration,
AGP metadata, acknowledgement plist and actual artifact/library bytes. These are local
observations, not a signed/reproducible-build attestation. Build timestamps/UUIDs may change hashes.

The normal app IDs, non-debuggable APK metadata and iOS simulator platform are required before
export; lab/other/debug/device products are rejected. ZIP names, duplicates, links, encryption and declared size limits are checked before inspection;
there is no extractall. Only bounded native-library bytes are written to a temporary file for
readelf, removed automatically. App-directory symlinks are rejected. XML DTD/entities are denied;
license URLs are metadata only and never fetched. Cache matches require actual SHA256 equality;
missing metadata/artifacts and mismatches cannot be promoted to VERIFIED. Workspace links must
resolve to an actual lock record; workspace/build/dev records retain their distinct scope.
Only relative artifact/lock paths, hashes, component/version/license declarations, import
basenames and declared permissions/privacy categories are retained. Full license text and user
paths are not exported. The app-tree digest uses a canonical sorted list of relative file names,
sizes and hashes, then discards that list; reproduce it from the same supplied app directory.

Build with the existing installed toolchain only. Android: JDK17, explicit ANDROID_HOME,
`./gradlew --offline --max-workers=2 :app:assembleRelease :app:testDebugUnitTest :app:lintRelease`.
iOS: use a private copy of cached Pods with both release archives already present; generate
missing inputs with existing `react-native/scripts/generate-codegen-artifacts.js -p apps/mobile
-t ios -o apps/mobile/ios`, then `xcodebuild` the existing Eilo workspace/scheme, Release,
generic iOS Simulator destination, separate derived-data directory and CODE_SIGNING_ALLOWED=NO.
Do not run pod install/npm install or fetch missing dependencies automatically. No build artifacts,
cache/POM files, dependency source, raw logs, credentials or binaries are committed/uploaded here.

## Validate without artifacts or caches

From Eilo:

```sh
python3 -m unittest discover -s packages/build-inventory -p 'test_*.py' -v
python3 -O -m unittest discover -s packages/build-inventory -p 'test_*.py' -v
python3 packages/build-inventory/inventory_report.py --output /new/inventory-report
```

`observed.json` is the closed recorded inventory, not a shipping-component allowlist. Tests cover
unsafe archives/symlinks, missing/ambiguous dependency digests, cache mismatch, XML entities,
workspace links, privacy unknowns, resource leaks, stale pins and forbidden acceptance promotion.
The JSON/HTML exporter refuses overwrite. CI validates recorded schemas/consistency/pins; it does
not reproduce original binaries, authenticate their build provenance or certify observations.
Only the two observed inventory summaries are uploaded with seven-day retention. These are actual
artifact observations with synthetic contract tests, not synthetic artifact measurements.

Remaining S17 work includes full shipped-component/source mapping, transitive/source notices and
redistribution review, signed device/archive provenance, required-reason API review, calibrated
process-attributed network observation and physical/runtime persistence/failure/endurance tests.
S08/release stays HOLD, persistent memory disabled, license approval NOT_GRANTED, SBOM completeness
NOT_ESTABLISHED, physical gates OPEN and network/privacy acceptance NOT_ESTABLISHED.
