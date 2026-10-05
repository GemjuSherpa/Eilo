# Eilo prototype review


Current revision: 2 October 2026 · UX review approved by the owner. Neon account database and authentication direction authorized. Native implementation and release validation remain outstanding. Historical phase/approval statements below do not describe current completion.

2 October 2026 · Design 1.2 · UX owner review approved

## Review method

A designer heuristic walkthrough covered visibility of status, user control, consistent navigation, recognition over recall, error prevention, recovery and privacy comprehension. Eighteen local browser checks exercised synthetic journeys and responsive constraints. Twenty-two semantic colour-pair calculations passed their defined contrast thresholds. The screenshots were visually inspected. These are prototype checks, not validation of the native product, participant usability or mobile accessibility compliance.

| Finding | Resolution | Evidence |
|---|---|---|
| Microphone permission could be mistaken for background consent | Separate controls; background defaults off; finish leaves capture stopped | Onboarding and Start fixtures |
| Cancelled privacy switch could visually show an unsaved choice | Re-render previous effective state before authentication; Cancel preserves it | Privacy cancellation check |
| Lock while correction sheet was open could expose an example fact | Close and clear sheet on lock; redact memory; unlock still needs authentication | Lock-race prototype check |
| Storage-full notice led to an inconsistent usage example | Full/80% states show250/200MB in the illustrative storage view | Full-storage check |
| Headphone disconnection could imply automatic speaker transfer | Pause, explicit confirmation and cancellation path | Route check |
| Oversized text could overflow inside the phone frame | Wrap headings/actions, flexible rows and scrollable content |320/390px checks at100%/200% text |
| Stop could fall below the fold while text is enlarged | Pinned active-listening Stop control; Stop in active sheets | Visual/interaction inspection |
| Dark palette could hide control boundaries | Semantic role pairs, distinct outlines and text labels | Contrast checks and dark screenshot |
| Fixed settings layout could push navigation away | Scroll content independently; navigation remains outside content | Rendered settings screen |

## Checks actually run

- JavaScript syntax and browser runtime checks.
- Explicit Start/permission denial and grant.
- Activation → reply → interruption → Stop.
- First-use separate history choice and stopped completion.
- Memory authentication, correction, cancelled deletion and source deletion.
- Cancelled privacy switch preserves its effective value.
- Explicit private mode preserves older example history.
- Lock closes sensitive sheet; unlock does not grant memory authentication.
- Background-off exit stops the simulated state.
- Full storage and speaker confirmation paths.
- Sixteen Home/recovery state previews render.
- Horizontal page/content bounds at320px and390px,100% and200% text.
- No prototype remote requests and no browser runtime errors.

The renderer is an isolated Chromium131 used for local QA, not a supported product browser requirement. The first automatic renderer download failed; a separate local-only renderer completed the checks. Neither is bundled in the prototype. All18 previously recorded checks pass in the recorded final run. No real microphone/audio/storage/key/model functionality is implemented by these checks.

## Pending evidence

Participant usability testing: **not run**. Native VoiceOver/TalkBack, Dynamic Type/platform font scaling, platform screenshot protection, actual system dialogs, offline voice quality, wake accuracy, end-to-end latency, encryption, backup exclusions, phone background execution and device battery/RAM: **not tested**. Existing10.5GB host-capacity note remains deferred. No users were recruited or messaged.

Recommended later usability study tasks: independently understand whether history is saved; start and stop listening; explain standby versus active conversation; cancel a privacy change; choose private mode; correct/delete a source; understand generic locked-screen limits; recover from full storage and headphones disconnect. Record outcomes and issues rather than assuming success from the prototype.

## Approval boundary

The user authorized completion of the UI/UX design package as a batch. Prior intermediate design approval gates were not treated as permission to implement the app. The finished design handoff awaits owner review; product UI development stays gated on VC-UX-14 approval. User testing and device verification remain separate later work.



## Current account and privacy baseline — 2 October 2026

The owner authorized Neon PostgreSQL for minimal account persistence and authentication, retaining social sign-in and device-local conversation history. This replaces the earlier no-user-database/stateless-relay proposal. The implementation design below is ready for review; no database, hosted service or app has been provisioned.

### Selected architecture

**Database:** Neon PostgreSQL. **Authentication:** Better Auth service backed by Neon PostgreSQL, with email/password and Google, plus Apple on iOS. Keep guest conversation equally usable and free. Select pinned versions at the native feasibility task; native capture/inference remains outside authentication. Better Auth's documented React Native route uses its Expo integration. Assess Expo modules/custom native development builds in the React Native project; Expo Go is insufficient for the voice engine. Do not assume compatibility before device tests.

Neon's managed authentication (currently documented as Managed Better Auth) stores users/sessions/auth configuration in Postgres, but its roadmap lists web frameworks and Google/GitHub/Vercel providers, not React Native or Apple. Therefore the implementation route is a separately hosted Better Auth service using Neon as its Postgres database. Hosting provider selection is pending. It is not claimed that Neon hosts this custom service. Do not silently substitute another database or remove Apple to use managed auth. Reassess managed auth only if documented native/provider support meets the requirements. PostgreSQL stores identity; it is not itself an authentication protocol.

Native app → HTTPS auth/account service → Neon PostgreSQL. Apple/Google authenticate through native/system flows. No SQL connection string, owner credential, server secret or raw database access in the mobile bundle. An account API verifies the authenticated session and derives the subject server-side. Enforce per-user access plus least-privileged database roles; test denied cross-account reads/updates. RLS may add defence in depth, but must be explicitly configured and tested rather than assumed.

### Minimal account data contract

| Data | Persistence and purpose |
|---|---|
| Immutable account ID | Remote identity and authorization |
| Verified email and verification state | Email access, recovery and account communication |
| Name/display name | Optional, editable, no legal-name requirement |
| Creation/update timestamp | Account lifecycle only, no conversation activity timestamps |
| Provider identity links | Framework-managed provider/subject; no email-only automatic merging |
| Password hash, sessions and verification records | Framework-managed lifecycle data, never plaintext passwords; bounded expiry/cleanup |
| Provider tokens where required | Sensitive lifecycle secrets, minimize scopes/retention, restrict access and use documented framework encryption/key handling |
| Account consent/privacy version | Minimal record of the account disclosure accepted; local history/background choices remain local |

Use the auth library's generated schema/migrations rather than inventing table names or directly editing managed internals. Application profile extensions refer to the immutable auth user ID. Avoid duplicate email/name copies where the auth user record already provides them. Document exact required fields after pinning the implementation version. No profile photo ingestion, location, contacts, advertising IDs, chat timestamps, emotions, audio, transcripts, facts, embeddings, prompts, local keys or personal models in Neon. No conversation tables, history-upload API, object-store archive or training pipeline in this release.

### Authentication journeys and account lifecycle

- Optional email sign-up/sign-in plus Google, and Apple on iOS. Display privacy disclosure before account creation. Optional name may be edited later. Verified-email policy, verification resend, reset and recovery are handled by the auth service; messages never include conversational data. Account forms may require typing; core conversation does not. Rate-limit/enumeration protections, session expiry, CSRF/nonce/redirect rules, password validation and secure cookie/device credential storage are tested before release.
- First use: optional identity choice or skip → explicit local-history consent → optional background consent/readiness → Home stopped. The review prototype may open on Home; it is not first-install routing evidence. A separate welcome page remains unimplemented, as discussed and accepted. Returning users open Home with actual native state.
- Sign-in, password reset and social success never start capture, grant history consent, recover history or unlock Memory. Use separate device authentication for personal data and privacy changes. Auth outage/expiry/revocation leaves offline guest conversation usable. Do not treat cached identity as authorization to a remote API.
- Normal sign-out requires local authentication, stops capture/context, clears this device's identity/session and preserves encrypted local memory with disclosure. Different-identity switching requires local authentication and explicit destructive reset before association; no automatic email linking. Framework account linking is disabled until a separately authenticated explicit linking flow is designed.
- Remote account deletion requires fresh account reauthentication; local personal-data deletion separately requires device authentication. Revoke all Eilo sessions, remove profile/identity/verification records under the approved retention policy and revoke provider grants where supported. Delete current-device personal state only after explicit local confirmation. Other devices cannot be remotely wiped; on confirmed account invalidation they close identity and require local reset before a different identity links. Offline local history remains device-protected and cannot be claimed remotely erased.
- Offline deletion: stop and erase local personal state if confirmed, show remote account deletion/revocation pending, retain only the minimum protected retry state until resolution. Never display remote success before service confirmation. Provide in-app status/retry and an authenticated public web deletion path for users who uninstalled the app. Delete Eilo's account, not the person's Apple/Google account.

### Retention, privacy and operations

Active account records persist until account deletion or until no longer needed for the declared purpose. Proposed active-system deletion target: within7 days of a verified request; sessions revoked promptly. Backup/point-in-time recovery/replica/branch retention and vendor logs require a documented finite schedule before launch. The7-day target does not claim immediate removal from backups. Restore must reapply deletion records so deleted accounts do not reappear. Keep only narrowly justified deletion/security records with explicit purpose and expiry; no indefinite account-event history. A precise backup horizon and deletion-proof method remain implementation/release gates.

Account PII exists in Neon, auth infrastructure, email delivery and provider systems. Review region availability, cross-border access/subprocessors, contracts, provider logging, retention and incident response. An Australian DB region alone does not establish Australian-only processing. Encrypt transport and storage, keep secrets/keys separately controlled, prevent credential/request-body logging and redact necessary operational diagnostics. Do not promise “no retained auth information”: users, sessions, verification and provider links are deliberately retained for authentication. No behavioural analytics or conversation telemetry.

Neon branches/backups can duplicate identity/session data. Production data must not be cloned into developer/preview branches. Use isolated synthetic accounts, distinct OAuth credentials and least-privileged CI access. Tests cover migrations, authorization, session lifecycle, deletion, restore, connection pooling, cold starts and service costs. Free conversation does not mean free account hosting/auth/email/model distribution.

Australian regulatory assessment: basic account storage is not inherently prohibited. Applicability depends on entity/business scope, including turnover and exceptions such as health-service provision. Do not rely on a startup exemption without assessment. The applicable requirements include collection necessity/notice, permitted use, access/correction, security, retention/deletion, overseas disclosures and breach response. The app remains casual adult conversation, not claimed mental-health treatment. Legal/privacy assessment and actual provider contracts are release gates, not completed legal clearance.

Cloud conversation history is technically possible but not approved. Encryption at rest with server-held keys still allows the service to read content. A later optional client-side end-to-end encrypted backup could reduce server content exposure but requires a separate key/recovery, consent, deletion and multi-device design. Do not add even ciphertext history to Neon in this release. No personal training uploads.

### Consolidated review and evidence

| Area | Position |
|---|---|
| Original vision | Friendly free voice conversation first; calls/camera/app actions and live browsing deferred |
| Models | Moonshine Small Streaming; Qwen3 1.7B Q4_K_M CPU evaluation; installed offline system TTS. Kokoro deferred |
| Preparation | Moonshine verified; Qwen source/environment verified, conversion unfinished; RAM note deferred |
| Local memory | Explicit consent, encrypted local text/derived data,90-day default,250MB personal store; private sessions save nothing |
| Background/lock | Explicit opt-in, platform-native lifecycle; generic locked conversation; native feasibility unproven |
| UI | Eilo / I am here for you; warm-neutral/teal light and dark; simulated account/voice/privacy screens |
| Evidence | Earlier18 synthetic prototype groups and22 palette pair checks; no real OAuth/database/native/security/participant pass |
| Primary risk | Real-phone quality/latency/battery and iOS background availability; protected locked-memory composition |
| Account tradeoff | Identity/recovery of account access provides no conversation recovery. Destructive identity switching needs usability review |
| Document correction | Current system TTS replaces old Kokoro recommendations; later decisions supersede historical approval wording; current check report controls counts |

### Sources and pending verification

Verified2October2026; publisher docs establish available integrations, not measured Eilo performance:
- Neon auth overview: https://neon.com/docs/auth/overview
- Neon supported frameworks/providers: https://neon.com/docs/auth/roadmap
- Neon production requirements: https://neon.com/docs/auth/production-checklist
- Better Auth native integration: https://better-auth.com/docs/integrations/expo
- Better Auth Apple: https://better-auth.com/docs/authentication/apple
- Better Auth PostgreSQL: https://better-auth.com/docs/adapters/postgresql
- OAIC small business: https://www.oaic.gov.au/privacy/privacy-guidance-for-organisations-and-government-agencies/organisations/small-business
- OAIC APP3 collection: https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-3-app-3-collection-of-solicited-personal-information
- OAIC APP8 overseas disclosure: https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-8-app-8-cross-border-disclosure-of-personal-information
- OAIC APP11 security/retention: https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-11-app-11-security-of-personal-information

User authorization covers this account-storage direction and document revision. Review the detailed service/native integration, retention/deletion and privacy design before its implementation task. No application development, infrastructure creation, credentials, database migrations or deployment occurs in this documentation task.


## Owner approval — 2 October 2026

The owner approved the UX review: “great. approve the ux review.” This approval covers the reviewed design baseline, including account journeys, guest access and privacy controls. It does not establish native feasibility, participant usability, mobile accessibility compliance, authentication implementation or production readiness. Historical pending-owner statements in this review are superseded by this record. The existing task tracker is unchanged in this decision-only revision; reconcile its UX approval fields when preparing the development board.

## Design merge 5 October 2026

Owner authorized incorporation of the standalone ripple/result/overlay design and default spoken-response text into the project. Design2.0 is finalized as a specification and26 implementation tasks, not a native completion claim. Prior2October approval remains evidence for the earlier design. New palette contrast, participant accessibility/usability, outside-app/privacy races, search/provider/media and physical-device tests are not run. JSON/CSV UX approval fields are now reconciled. Historical prototype1.2/screenshots/check report do not validate Design2.0.
