# S09 — native protected keys and lock authorization

The user authorized all eight S09 tasks continuously, separate task branches merged into
`sprint/s09-protected-keys` and one final review PR. Base is reviewed PR71/main `77574d9`.
No main merge is authorized. Local native implementations and the inbox design review are
prepared for review; **S09 physical/security acceptance is partial**, and the inbox composition
is explicitly NOT_APPROVED_FOR_IMPLEMENTATION. S08 HOLD still blocks S10 persistent storage.

| Task | Task branch suffix | Delivered / acceptance limit |
| --- | --- | --- |
| VC-KEY-01 | vc-key-01-ios | Explicit iOS Keychain provider and owned native key; real OS auth/passcode/lock tests NOT_RUN |
| VC-KEY-02 | vc-key-02-android | Explicit Keystore AES-GCM wrapping/unwrapping; API35 floor; real ART/Keystore/auth/invalidation tests NOT_RUN |
| VC-INBOX-01 | vc-inbox-01-review | Threat/composition review; unresolved library/format/interoperability/key association blocks encryption implementation |
| VC-KEY-03 | vc-key-03-session | One-use authentication tickets, native session and automatic expiry; no app authentication driver installed |
| VC-KEY-04 | vc-key-04-release | Registered native-copy revocation, explicit iOS auth cancellation; no live database exists to close |
| VC-LOCK-01 | vc-lock-01-transition | Privacy invalidation before voice cleanup in both controllers; safe stopped fallback, no locked voice activation |
| VC-LOCK-02 | vc-lock-02-privileges | Native origin/operation predicate denies wake/voice/model privileges even during a screen-authenticated session |
| VC-LOCK-03 | vc-lock-03-reentry | Unlock alone denies memory; fresh authentication required; Stop/old callbacks/expiry/clock rollback revoke access |

Branch prefixes are `task/s09-`. `task/s09-final-review-evidence` adds review regressions and
validation. All seven code tasks had same-iPhone18 Pro build/install/three fresh ten-second
launch checks before commit. The design-only inbox review required no app rebuild. Three final
code refinements each received another full build/install/three launches: 30 launches total.
No hardware inventory or physical authentication trial is inferred from those launches.

## Provider and key lifetime boundaries

The iOS provider uses fixed native service/account identifiers, synchronizable=false and
SecAccessControl with WhenPasscodeSetThisDeviceOnly plus userPresence. Explicit creation fails
on duplicate; reads never generate a replacement for a missing/invalidated key. Reads use a
fresh LAContext with biometric reuse disabled; cancel invalidates the current context. Creation
and reads require a separately supplied current eligibility predicate, which defaults to false.
No app startup path constructs or calls this provider, or provisions a Keychain item.

Android uses an AndroidKeyStore AES256/GCM/NoPadding key with randomized encryption,
authentication required, a five-second strong-biometric/device-credential window and
unlocked-device required. API35 is an explicit floor because documented unlocked-device issues
on older versions prevent claiming this policy there. Wrapping uses a fixed version/domain AAD,
12-byte provider-generated nonce and 128-bit tag for exactly one 32-byte database key. Ciphertext
and IV are defensively copied and length checked. Provisioning is serialized within this app
process and refuses an existing alias; reads never silently regenerate it. Failures are mapped
to a safe generic native exception without raw causes. No key is generated/read in host tests.

These are native providers, not an end-user memory feature. A future trusted screen driver must
perform fresh explicit OS authentication, supply a current unlocked/secure-device predicate,
connect iOS cancellation to privacy teardown, and persist only wrapped material in appropriately
excluded app-private storage. Those production UI/store/backup integrations and actual device
API behavior are not established by compilation or scripted authorization tests. No key bytes,
ciphertext, prompt or authentication result cross the React Native bridge in this sprint.

Owned keys expose a synchronous native borrow only. Sessions register at most eight additional
owned copies, all revoked on close/lock/Stop/expiry. Darwin-owned Swift key storage uses explicit memset_s erasure; JVM owned arrays are filled
with zero. Intermediate buffers are overwritten where owned; Swift COW, JCA/OS internals, malicious borrower copies and whole-process RAM erasure
are not guaranteed. Future consumers must use bounded synchronous borrows, retain no pointer or
array copies, and revalidate transactions immediately before committing or publishing output.
A failed final authorization check cannot undo side effects already performed by a bad consumer.
There is no database, key reset, rotation, migration, recovery or deletion implementation here.

## Authorization and controller integration

Authentication starts with a native ticket before work is scheduled; only the matching pending
ticket may consume a provider result within 30 seconds. Session lifetime is 60 seconds, bounded
by a native monotonic clock and a scheduled revocation; accesses also reject expiry/rollback.
These conservative values and the provider policy need review, not automatic release approval.
Denied reads during a pending authentication do not consume its ticket. Replaced/expired/closed
sessions reject old auth results and old timers cannot invalidate a newer session.

PrivateEffectGate gains a default no-op invalidation hook for compatibility. Both native
controllers invoke it before privacy cleanup and on every Stop; MemoryKeySession revokes keys
and registered copies. Existing default gates remain denied. Private effects check current
authorization after synchronous work as well as before it; stale results cannot report success.
Unlock invalidates the old capability and does not restore it. The privilege predicate accepts
only a trusted authenticated-screen origin and a current session; origin is never inferred from
model or voice text. It is a permission predicate, not user intent or a delete/settings dispatcher.

Real generic locked conversation remains blocked by VC-AUDIO-09/10 and S08. Controllers retain
their safe stopped state on lock rather than pretending background audio can run. Screen-off
permissions, model readiness, release trust, physical feasibility and persistent-memory gates
are unchanged. Only reviewed source checksums in the S08 decision/audit links were refreshed.

## Checks and remaining acceptance

Final checks: 305 Swift / 361 Android tests, zero failures/errors/skips; Android lint, Debug/Release
compilation/builds; workspace lint/typecheck and nine mobile/33 contract tests; 47 feasibility
regressions ordinary/optimized plus all six pending reports. Staged/full new-history secret
scans precede publication. Source/build hashes and exact task commits are in S09_VALIDATION.json.
Original personal Xcode/plist/S02 edits remain byte-identical and excluded; temporary dependency
links are removed. No packages/models/datasets were installed/downloaded; no microphone, OS key
provisioning, real authentication prompt, store, deployment or paid service was activated.

Focused tests cover key bounds/close/owned-buffer overwrite (JVM), wrapped-envelope defensive
copies, denied provider defaults, auth timeout/late/duplicate results, stale timer, eight-copy
limit and revocation, lock during capture/generation/playback, exhaustive origin/operation denial,
unlock/re-authentication, Stop while auth is pending, backward clocks, final expiry recheck and
benign read denial while authentication is pending. They use synthetic keys/effects, not user data.
Physical protected-data/key-invalidation/auth failure/passcode/biometric changes, backup/transfer
behavior, hardware security level and end-to-end OS auth flows remain NOT_RUN. No independent
security audit or complete physical acceptance is claimed. The unresolved inbox composition
remains blocked as documented in S09_INBOX_COMPOSITION_REVIEW.md.

## Primary policy references

- [Apple device-only passcode accessibility](https://developer.apple.com/documentation/security/ksecattraccessiblewhenpasscodesetthisdeviceonly)
- [Apple keychain access controls](https://developer.apple.com/documentation/security/restricting-keychain-item-accessibility)
- [Android key generation/authentication policy](https://developer.android.com/reference/android/security/keystore/KeyGenParameterSpec.Builder)
- [Android unlocked-device limitations](https://developer.android.com/reference/android/security/keystore/KeyProtection.Builder)

Review the native implementation and policy limits. Do not close S09 acceptance or start S10
persistent history solely because these local checks pass; S08 and the remaining native/physical
security evidence are still required.
