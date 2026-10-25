# S17 dependency — actual normal build artifact inventory

On 26 October 2026, normal Android release compilation, 380 unit tests and release lint passed
offline. An unsigned iOS simulator Release build passed using an isolated clone of existing cached
Pods/release frameworks, after generating missing local React Native codegen inputs. Initial
failed-build evidence is retained. No personal dependency configuration was switched. No device
install/launch, signing credential inspection, new package/model download or distribution occurred.

`packages/build-inventory` now inspects real artifacts using existing readelf, aapt2 and otool:
52 APK native libraries (four ABIs) and four iOS native binaries, with exact hashes and dynamic
import names; manifest permissions and eight iOS privacy declarations are preserved as declarations.
The inspected artifacts contain no files matching the configured audio/model extensions. This
bounded resource check is not proof of no embedded content, private files or device persistence.
INTERNET permission is present and is not converted into a no-egress claim. The APK uses existing
development-signing configuration; the iOS product is unsigned simulator Release, not a device
archive. Signing and privacy acceptance remain unreviewed/unestablished.

The co-observed AGP report contains 108 Maven entries: 100 artifact digests match cached bytes,
eight have no recorded digest. One POM lacks a direct license declaration. The npm lock contains
940 non-link records including build/dev dependencies; five lack a declared license field.
CocoaPods has 149 lock entries including subspecs and six acknowledgement records including a
generated footer. These sources do not establish full shipment mapping or transitive notice/
redistribution compliance; no legal approval or complete SBOM is inferred. The report retains
these gaps, rather than equating metadata presence with acceptance or missing declarations with
an absence of licensing elsewhere.

The collector requires normal-app IDs, non-debuggable APK metadata and the simulator platform,
rejecting lab/other/debug/device products. It validates bounded ZIP paths/duplicates/links, rejects directory symlinks and XML
DTD/entities, requires actual cache-byte matches and retains unknown privacy declarations as null.
Exports contain relative public artifact paths, hashes and dependency/declaration metadata only,
without raw binaries, notices, logs, personal paths, provisioning identities or audio. Strict
schema/pin/resource/scope checks and synthetic regressions run offline in CI. Only JSON/HTML
inventory summaries are uploaded; CI does not authenticate the original build observations.

This closes a concrete artifact/dependency inventory subtask, not VC-VERIFY-07 or VC-VERIFY-11.
Full binary/source and transitive license review, signed-device provenance, independent privacy
and physical/runtime gates remain open. S08/release HOLD, memory disabled and supported release
configurations empty remain unchanged. No production confidence, networked feature or history
capability is activated.
