# S17 integrated audit: source review and remaining evidence

Reviewed 2026-10-22, main `f666a7ca8af75b21401e94e777843e83d77f76bb`. Scope is repository source and existing aggregate reports only. No phone connection, capture, packet observation, logs, personal files, credentials, backups or app-container inspection was performed. Source inspection cannot establish runtime traffic absence, encryption, secure erasure or physical failure safety.

## VC-VERIFY-07: network/privacy

The Android pack installer uses a dedicated OkHttp client with no cookies, authentication, cache, proxy, redirects or connection retries. Its transfer layer bounds response size against signed manifest artifact size and applies configured HTTPS-origin checks. The iOS native seam uses an ephemeral URLSession configuration with cache, cookies and credential storage disabled. These are generic model-distribution paths, not a conversation transport, and the app's INTERNET permission alone is not evidence of egress. Inspecting these sources does not inventory every transitive SDK or delegated OS path. Actual current release-build dependency/binary inspection and calibrated process-attributed observation remain necessary.

The S15 search gateway is a disconnected server-only reference boundary, with no shipping adapter, listener, approved provider/funding or HTTP transport. Offline denial tests do not establish network behavior of a future adapter. Native confirmation must precede even query-free nonce setup; accepted query and proof travel together only afterward. Optional identity providers are unconfigured. No networked feature is activated by this audit.

`IOS_NETWORK_RETEST_REVIEW.md` and the RVI aggregate records document actual historical attempts. Instruments 27.1 still crashed; the RVI positive calibration recognized no attributed markers. Calibration-match counts are not traffic counts. Traffic metrics remain null and network acceptance NOT_RUN. Do not repeat the observation automatically, claim zero traffic, or broaden capture/destination scope. A reviewed successful target-attributed positive calibration is required first; future physical observation needs current scope/permission review.

## VC-VERIFY-08: persistence/backup

AndroidConsentPersistence writes an explicit allowlist of version, history choice, disclosure version, background consent, volume and display choices to local SharedPreferences. This is control metadata, not encrypted conversation storage. S14's presentation is volatile and clears on policy/lifecycle changes; reference release is not certified erasure. The iOS privacy manifest declares UserDefaults usage. None of these proves native database/WAL/temp/backup encryption.

S10 SQLCipher/personal-memory work remains gated by the unaccepted S08 feasibility decision. No production encrypted conversation store, backup/restore acceptance, signed-out identity reset path or actual private-history integration is inferred from fake capabilities. Required future inspection covers DB/WAL/journals/temp/inbox/exports, logs/notifications/snapshots, crash diagnostics, caches and platform/cloud backups with synthetic markers, correct-key/keyless tests and native lock transitions. String search alone cannot prove encryption or absence of copies. No personal store is enabled for testing this audit.

## VC-VERIFY-09: resource failures

Existing native policies and synthetic regressions exercise denial, cancellation and unavailable capabilities. They do not prove committed-ciphertext preservation under disk/memory/thermal/battery events: VC-STORE-08 and the joined native store/runtime are unaccepted. Freeze per-device baseline, failure-injection mechanism and post-failure integrity checks before collection. A safe pause must never silently retry with plaintext, cloud inference or forgotten history; report unsupported OS injection rather than simulating a physical pass. Do not stress the connected phone or fill its disk to manufacture a result.

## VC-VERIFY-04/-05/-06: endurance and standby

Existing voice-latency tools already define foreground60min, screen-off60min and8h standby schedules, aggregation and explicit NOT_RUN records. Reuse them rather than create duplicate workloads or infer fresh measurements from old model diagnostics. Freeze supported physical device/build, corpus/model/route, initial battery/thermal conditions and charging state first. VC-VERIFY-01, native joined turns, wake/background eligibility and independent acoustic/network observation remain open. Foreground tests need the same exact workload and final15min acoustic targets; process-only simulator dwell is not endurance evidence. Android needs independent physical evidence.

## VC-VERIFY-10/-11: closure and release

The requirement ledger maps every requirement ID actually listed in the planning issue source to its planned tasks and pinned supporting records. Supporting records are context, not full-app requirement passes. Each requirement remains explicitly BLOCKED pending integrated acceptance; even accepted historical UX/local unit tests cannot establish current full-app release acceptance. This audit intentionally includes requirements beyond the original F01–F19/S01–S10/A01–A16 closure list so later visual/search/surface requirements cannot disappear.

Release package preparation can inventory missing items now; actual supported-device certification, complete shipped license/SBOM review, signing provenance, privacy disclosures, rollback/pilot acceptance and distribution remain blocked. No account, service, store submission, build upload or release is authorized by the ledger. S08 remains HOLD, supported configurations empty and persistent memory disabled. Passed CI approves repository preparation only.
