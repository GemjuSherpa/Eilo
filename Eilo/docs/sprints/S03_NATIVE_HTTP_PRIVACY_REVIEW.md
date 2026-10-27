# S03 — native installer HTTP privacy boundary

The existing installer tests substituted `PackHTTPClient`, so their fake responses did not inspect
the actual URLSession request. `NativePackHTTPClient` now sets request-level cookie handling off,
ignores the local cache explicitly and uses a 15-second request timeout, matching its existing
ephemeral session policy. It also rejects non-HTTPS and URL-embedded credentials before session
creation. The higher transport layer still owns the origin allowlist, manifest bounds, redirect
limit and response/ETag/range checks. No production origin, trust key or license approval is added.

The normal public initializer retains the ordinary URLSession protocol stack. A module-internal
initializer permits test protocol classes; it is used only by XCTest. Each fixture session installs
a protocol that intercepts every request and returns synthetic responses or local errors; unknown
URLs fail locally instead of falling through to HTTP. Nothing is registered globally, no shared
cookie/cache/credential store is changed, and no test contacts a provider or opens a microphone.

Eleven new native adapter tests verify:

- The actual ephemeral configuration has no cache, cookie store or credential store, with cookies
  disabled, bounded timeouts and the existing TLS minimum.
- Insecure, local-file, malformed and credential-bearing URLs are denied before interception.
- GET/identity/generic installer headers, absent cookie/auth/proxy-auth/body fields and explicit
  request cache/cookie/timeout flags survive into the intercepted native request.
- Streaming bytes and exact resume Range/If-Range behavior work; a synthetic response cookie is
  not replayed on a later fetch.
- 401, wrong length, encoded data, wrong resume range, short/oversized bodies and foreign raw
  redirect responses fail; invalid ranges preserve the prior partial, and body writes stay bounded.
- Pending-task cancellation finishes with the cancellation error, while pre-cancelled and local
  network-error fixtures produce no response/body. Cancellation starts after interception, avoiding
  a scheduler-dependent delay assumption. Body assertions allow URLSession chunk coalescing.

These are offline macOS Foundation/XCTest adapter observations, not TLS handshakes, proxy/DNS
behavior, authentication-challenge or OS automatic-redirect observation, actual provider logging,
packet attribution, iPhone behavior or evidence of zero traffic. A raw fixture 302 tests manual
transport/origin denial; it does not simulate URLProtocol's separate redirect-notification path.
Independent process-attributed privacy observation and hosting retention review remain required.

The changed source invalidated two current simulator/host evidence inventories, as intended.
Signed VAD/ASR installer cases and the file-fed simulator capture/reply fixture are rebuilt and
rerun before their current source/report pins are updated. Prior results remain in Git and local
backups; physical device/build provenance is historical and is not re-pinned to this code. Earlier
S17 artifact inventories also describe their original exact binary hashes, not the newly built app.

Validation: all 336 Swift tests, strict native device/simulator typechecks and a normal unsigned
simulator Release build passed, together with fresh eight-case simulator and host-JNI installer
runs, the three-case joined simulator fixture and all eleven offline workflow steps. Hosted PR
checks remain required before merge. Initial local build-path and fixture chunk assumptions were corrected;
failed attempts remain in ignored local logs. No ordinary-app installation/launch, physical test, dependency
download, account, signing key, distribution or production runtime activation is part of this work.
Personal edits are preserved. S08/release HOLD, physical gates OPEN and persistent memory disabled.
