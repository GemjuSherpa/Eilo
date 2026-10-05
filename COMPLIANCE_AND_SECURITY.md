# Eilo — Compliance and Security Requirements

Version 1.0 | 5 October 2026

## Applicability, not certification
Eilo is a general consumer companion. No HIPAA certification or verified GDPR compliance is claimed. HIPAA was an example in the user's requested format, not an Eilo requirement. Australian privacy-law applicability, GDPR territorial/processing scope, consumer rules and store policies must be assessed for the actual entity, markets, providers and data flows before release. Encryption alone does not satisfy a law. The Australia-first adult pilot is provisional. Reassess before health-service partnerships, minors, new territories or tracking. The management plan's regulatory assessment and official references are starting points, not legal clearance.

## Mandatory data rules
1. Never upload raw microphone audio, full conversation transcripts/history, derived personal memory, emotion/personality profiles, exact GPS/location history or personal model weights/adapters. No corresponding server tables/endpoints exist in MVP.
2. Only minimal account/profile and auth-framework data may persist in Neon. Account/provider tokens are sensitive. Guest/offline core cannot depend on authentication availability.
3. Optional search is a narrowly defined exception: explicit preview/confirmation of a minimized query before each request. No personal context enrichment or automatic retry. Provider processing/query/network-metadata retention must be disclosed and reviewed. Text/image/video preference is not search consent.
4. History and derived memory require a deliberate local choice; private sessions persist no conversation content. Do not save raw audio. Bounded PCM exists only in native volatile buffers, including the proposed two-second wake buffer.
5. SQLCipher protects personal text/indexes/journals at rest. Keys use native iOS device-only non-synchronizing Keychain policies and Android Keystore wrapping/authentication. Keychain/Keystore store/wrap keys; do not claim they are bulk conversation databases. Select exact accessibility/OS-authentication policies through tests.
6. No history/key/inbox/personal model state in iCloud, Android cloud backup, device transfer or app-managed sync. Verify actual backups and library caches. A login on a new phone cannot restore local history.
7. No personal information, content, queries/results, emails, tokens, secrets, provider URLs with sensitive query strings or raw network bodies in console, logs, crash reports, analytics, traces, CI artifacts, notifications or support bundles. A redactor is defense in depth, not permission to collect content.
8. Notifications/locked surfaces contain generic operational status only. On lock/Stop/account/privacy transitions clear current cards, private context and transient caches; cancel/epoch-invalidate pending callbacks. App-switcher snapshots must not expose personal views.
9. Prevent personal keys/history from entering JS. Volatile authenticated Memory display data is allowed only when necessary, paginated and cleared; no Zustand/global persisted/cache copy. Native plaintext buffer lifetime is bounded.
10. Ambient wake is not authentication. Device authentication is separate from app login. Memory review/deletion and sensitive consent changes require authorized local device access. Never treat voice matching, an OAuth token or a public inbox encryption key as device authentication.

## Locked operation and encryption gate
Permit only explicitly selected generic locked conversation within OS rules. Existing history is inaccessible. On lock close the main store, cancel sensitive playback and clear owned decrypted key/context buffers. Proposed locked writes use a vetted sealed ciphertext inbox with protected private key and public encryption material; do not design homemade cryptography or weaken key protection to make a demo work. Standard envelope composition, integrity/nonce rules, file protection, crash import/deduplication and key association need review/native evidence. If the composition fails, document the requirement blocker and request a reviewed scope change.

## Retention and deletion
- Local personal ceiling: 250,000,000 bytes including facts/indexes/inbox/journals, generic models excluded. Proposed warning at 80%; reserve maintenance/write capacity and handle physical disk-full separately.
- 90-day default local retention, configurable. Expiry precedes retrieval. Source deletion/expiry removes or regenerates dependent facts/indexes so stale facts cannot return. Do not silently upload or drop authorized history when full; offer cleanup or an explicit private session.
- Delete-all cancels/invalidate work and removes local stores/inbox/keys under authenticated flow. Do not promise forensic erasure from flash or a compromised OS.
- Sign-out preserves local history unless explicitly erased. Account deletion handles remote identities/sessions separately; active deletion target is seven days after verified request, subject to actual provider/legal review. Never report deletion complete after a failed call.
- Operational metadata seven-day and minimal deletion/security record 30-day retention are planning assumptions, not blanket permission to collect fields. Define necessity, field allowlist, provider backup/PITR/branch retention and restore-deletion behavior before release. No query/body logging regardless of retention.

## Authentication and network
Use the pinned Better Auth framework rather than custom password/token crypto. Verify mobile browser redirects, PKCE/state/nonce wherever applicable, issuer/audience/signature validation, token expiry/refresh/revocation and fresh-auth deletion. Server derives identity; client cannot choose another account subject. Store mobile credentials under device-only native policies. Never bundle server/provider DB credentials in the mobile app.

Require HTTPS and verified certificates; target TLS1.3 with audited TLS1.2 compatibility only where needed. No insecure fallback or blanket certificate-validation bypass. Restrict outbound providers/origins/redirects. Search/media fetching validates MIME/length/schema/timeouts and prevents SSRF/private-network access. No arbitrary WebView HTML, autoplay or executable provider content. Minimize IP/rate-control metadata and document provider exposure.

## Model, media and application safety
Verify exact model/voice/runtime license rights and source/checksum/version before distribution. Treat model output and search snippets as untrusted, never permissions/tool commands. Policy checks apply before releasing speech clauses; do not imply small-model checks guarantee safety. Avoid unsolicited diagnoses, claims of sentience or exclusive emotional dependence. No calls/camera/app control/training integrations in MVP. External source links require deliberate user action; loaded media obeys rights and transient-cache rules.

## Secure engineering and release evidence
Use synthetic data in tests/previews/PR descriptions and disposable databases. Never collect real conversations for debugging or attach user recordings. Keep secrets out of the initially public GitHub repository, including historical commits. Least-privilege CI, trusted signing workflows, pinned/reviewed dependencies, environment isolation and secret scanning are required. Untrusted PRs cannot access signing/production secrets.

Required evidence: threat model/data map; actual native storage/key/backup tests; lock/Stop/privacy races; private-mode persistence/network audit; notification/snapshot inspection; native OAuth and deletion lifecycle; query confirmation/payload/provider retention; media caches/routes; license inventory; accessibility/device support; security review of locked inbox. Unit tests or an attractive mockup cannot substitute for these checks. Mark unavailable checks BLOCKED/NOT RUN with reason. Critical privacy/security defects block affected release.

No automatic compliance checkmarks, legal clearance, telemetry SDK installation or external reporting/messages are authorized by this file. Maintain an incident process without preserving user-content payloads as evidence. Follow verified applicable notice/reporting duties when assessed for actual operations.
