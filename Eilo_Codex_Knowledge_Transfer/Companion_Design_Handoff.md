# Eilo UI/UX design handoff

## Current merged baseline 5 October 2026

CR-2026-10-05-01 was authorized by the owner: finalize the ripple/results design and merge it into the project. Eilo Visual Interaction Design v2.0 is authoritative for updated visual/search/outside-app behavior; the following historical material does not override it. Core inference and all conversation history/derived memory remain local. Optional confirmed live search is a new external query flow, not cloud conversation inference. No app code, provider provisioning, device pass or deployment is implied.

- Home now uses a blue/light-purple theme and rounded centre-out ripples during listening/speaking; stopped/standby/thinking remain truthful and distinct. Accessible Start/Stop, Memory and Settings remain available.
- Spoken response text is the default fallback; rich cards show enabled text/images/videos with attribution and explicit media playback. Recommended initial defaults: text on, images/video off.
- Visual cards expire after20 seconds of actual inactivity after speech/processing/loading/video/interaction; pin and dismiss are explicit. The existing60-second conversation timer remains independent. Lock/Stop/privacy transitions clear personal display state.
- Android outside-app overlay requires separate opt-in, special permission and physical-device feasibility. iOS has a generic notification fallback; rich results may require opening Eilo. No generic cross-platform Siri overlay or guaranteed notification timeout. Locked surfaces remain generic.
- Search off by default, per-query preview/confirmation and minimized approved payload only; no transcript/memory/account ID/location history upload, no query/results in Neon or service logs. Provider/media licensing, retention, cost and real-device cache inspection block release until resolved.
- GitHub selected public initially/private later. Actions, EAS, Vercel and native test distribution remain the recommended stack subject to integration gates. Human task review, staging authorization and production/store approval remain separate.
- JSON backlog1.5 contains175 tasks across23 groups, including26 additions; design approval does not authorize their implementation. The2October UX approval is reconciled in JSON and CSV; old pending wording is historical.


## Historical baseline through 2 October 2026


Current revision:2October2026 · Neon account database and authentication direction authorized; detailed implementation design awaiting review. Historical phase/approval statements below do not describe current completion.

Version 1.2 · 2 October 2026 · Design package prepared for owner review

The complete proposed experience is represented in the interactive prototype, design tokens and the specifications below. This is a design artifact, not a working React Native app. Prototype conversations, authentication, model readiness and lock states are simulations using synthetic fixtures. No participant study, device accessibility certification, model inference, encrypted storage or actual background operation is claimed. Owner approval of the finished design remains pending.

## 1 Product brief and navigation — VC-UX-01

English-speaking adults should be able to start a casual voice conversation without typing or being required to create an account. The product is warm, respectful and clearly AI. The central design question is “Is it listening, and how do I stop it?” Privacy controls must be understandable without technical knowledge. Core conversation stays free, without an introduced daily quota. No streaks, urgency badges, advertising, emotional dependency prompts or notification campaigns.

Three persistent destinations: **Home** for Start/Stop and conversation state; **Memory** for authenticated history/facts and corrective actions; **Settings** for local preferences, privacy, listening and voice. Onboarding is a separate first-use flow. There is no mandatory chat transcript or input field on Home. Editing a remembered fact uses an optional text field; conversation itself never requires typing.

Product controls stay separate from the prototype's left navigation, theme picker and simulation panel. Those review tools must not ship in the app. The proposed product name is Eilo (AY-lo), with “I am here for you” on welcome/idle Home. “Hey Eilo” remains an untested activation phrase. Brand availability is not cleared.

## 2 Voice interaction — VC-UX-02

| State/event | Visible message | Spoken/cue behaviour | Exit/action |
|---|---|---|---|
| Stopped | Start when you’re ready. Your microphone is off. | No companion speech | Explicit Start |
| Standby | Say “Hey Eilo”. Wake standby | No unsolicited conversation; optional short operational cue only on state change | Wake phrase or Stop |
| Activation | Listening · Take your time | Short nonverbal cue paired with status; preserve question immediately after wake | User utterance |
| Capturing | Listening | Do not speak over ordinary user pauses | Native endpoint detector |
| Thinking | One moment. Putting a reply together on your phone. | No filler speech required; quiet processing | First meaningful clause, error or Stop |
| Speaking | You can jump in. | Brief warm reply, no claim of human identity | Intelligible user speech cancels old output; Stop |
| Unclear turn | Could you say that again? | “I didn’t catch that clearly. Could you say it again?” | New utterance; no durable uncertain fact |
| Interruption | Listening to your new turn | Stop old audio and queued clauses; no apology loop | New turn |
| End conversation | Wake standby | One short operational acknowledgement only if safe | Context clears; standby continues |
|60s inactivity | Wake standby | No unsolicited reminder | Timer begins after playback/processing ends |
| Stop listening | Listening stopped | Optional brief end cue; never delay stopping for speech generation | Mic and temporary context released |
| Call/resource interruption | Listening is paused/stopped | No forced speaker takeover or automatic revival | User Start after cause resolved |
| Lock transition | Memory locked; generic standby if permitted | Cancel sensitive reply first; no prior personal memory in new generic conversation | Unlock plus authentication for memory |
| Headphone disconnect | Headphones disconnected. Speech is paused. | No automatic private speaker playback | Explicit speaker confirmation |

Prototype timing demonstrates state order only. It is not an end-to-end latency benchmark. Operational cues never count as meaningful reply audio. Supportive examples acknowledge expressed feelings (“That sounds like a tiring day. Want to talk about it?”), without voice-based diagnosis or emotional certainty. Avoid “I need you”, exclusivity, human identity claims or pressure to continue. Explicit imminent danger receives reviewed guidance to contact local emergency help or a trusted person; no call, location lookup or monitoring claim. Final voice wording and safety quality remain human/model evaluation items during development.

## 3 Journeys — VC-UX-03

**First use:** optional identity choice (skip available) → introduction → explicit history save/not-save choice → optional background consent (off) → offline model/voice readiness review → Home stopped → Start → native microphone permission → standby. Onboarding never captures audio. A denied permission leaves Memory/Settings/help available and never loops prompts. Prototype “mark ready” is a simulation; the shipped app must show actual download size, connection choice/progress, cancellation and verified readiness.

**Everyday conversation:** Start → standby → wake + optional immediate question → listen → process → meaningful reply. Follow-ups do not need another wake phrase during the active session. Stop is always locally available. End conversation/idle timeout returns to standby; Stop releases capture completely. Home reflects the native controller's actual state when reopened.

**Private session:** authenticate before privacy change → explicit private selection → cancel ongoing work/Stop → Start new session. New transcripts, facts, indexes and inbox writes are disabled. Older saved history is unchanged. Leaving private mode is explicit and does not retroactively save private content.

**Outside UI/screen off:** no background consent means capture stops on exit. With consent, already-running permitted mode may continue. Lock clears private context and keeps earlier history inaccessible; only generic conversation is allowed. New history writes, when consented, require the sealed ciphertext inbox architecture. No UI claim of availability after OS termination, force-quit or reboot. Phone unlock alone does not authenticate memory.

**Review/correct/delete:** Memory → local authentication → bounded history/fact pages → select fact → view source/correct/delete source. Correction changes derived value with provenance handling; original text remains unless deleted. Source deletion invalidates dependent recall. Delete all uses a separate explicit destructive confirmation and clears personal state/keys/inbox, with saving off pending new consent. No undo or recovery promise after irreversible deletion.

## 4 Screen specifications — VC-UX-04 to VC-UX-07

| Screen | Main content and primary action | Required variants | Build mapping |
|---|---|---|---|
| Optional identity | Apple/Google or equally usable skip; no recording | Success, cancel, offline, retry, Android Google-only | VC-AUTH-01/02 |
| Intro | Local conversation, clear AI identity, optional encrypted text history, permanent-loss disclosure; Continue | Larger text, screen reader | VC-SET-01 |
| History choice | Two explicit radio choices; neither selected by default; Continue after choice | Not-saving path, consent explanation | VC-SET-02 |
| Listening/setup | Background switch off; lock/termination limits; model/voice readiness; Finish | Missing model/offline voice, failed/interrupted setup | VC-SET-03, VC-PACK-09, VC-VOICE-01 |
| Home | One central Start/Stop; status label and static wave mark; history/private indicator; background scope | Stopped, standby, capturing, thinking, speaking, clarify, paused, error | VC-SET-06, VC-CTRL-01 |
| Memory gate | Explanation and Authenticate | Locked, auth cancelled/failed, unlocked unauthenticated | VC-KEY-03, VC-MEM-04 |
| Facts | Confirmed/uncertain status, source link, Correct/Delete | Empty, corrected, expired/deleted, pagination | VC-MEM-01, VC-MEM-03, VC-MEM-04 |
| History | Bounded messages, interruption status and local date; delete-source action | Empty, interrupted, expired, deletion failure | VC-STORE-03, VC-STORE-04, VC-MEM-05 |
| Memory storage | Included personal usage, actionable threshold warning, retention/delete choices |80% warning,250MB full, disk/write failure | VC-STORE-07, VC-STORE-08, VC-MEM-05 |
| Settings | History/private/retention; separate background consent; installed offline English voice and volume | Authentication needed, OS unsupported, settings change stops/restarts explicitly | VC-SET-07, VC-SET-08 |
| Lock concept | Generic availability, memory-locked notice, illustrative OS control | Already-running permitted mode vs stopped | VC-LOCK-01, VC-LOCK-02, VC-AUDIO-09/10 |
| Recovery sheet | One clear reason and next action; Stop reachable when active | Permission, setup, route, resources, corrupt/missing asset, storage full | VC-PACK-09, VC-AUDIO-08, VC-VERIFY-09 |

No permission, privacy or destructive action is granted from the model's reply. The app does not show earlier private content in status indicators, operational notifications, app-switcher surfaces or locked views. Recovery messages do not repeat the failed utterance.

## 5 Content and recovery copy — VC-UX-08

- Privacy footer: “History on · encrypted locally”, “History off · not saved”, or “Private session · not saved”. These claims are release-blocked until native storage verification passes.
- Save disclosure: “Save conversation text and useful, reviewable memories on this phone. No cloud backup or sync.”
- Private choice: “Nothing from this session will be saved. Older history stays unchanged.”
- Background: “Continue outside the app. Off by default; available where your phone permits it.”
- Permission: “Eilo uses your microphone only after you start listening. You can stop at any time.” Use the real OS prompt rather than an app-designed replacement.
- Full storage: “Your local memory is full. Unlock to manage storage, or explicitly choose a private session. We won’t silently stop saving.”
- Missing model: “Offline models aren’t ready. Complete setup before starting.”
- Missing voice: “An offline English voice is needed. A network voice won’t be used.”
- Route change: “Headphones disconnected. Speech is paused.” Then explicitly confirm speaker playback.
- Restart: “Listening is stopped. Start again when you’re ready.” Never present stale “listening” status.
- Source deletion: “This removes its text and memories derived from it. It won’t be available for recall.”
- Delete all: “There is no cloud copy to restore.” Avoid forensic-erasure promises.

## 6 Theme and components — VC-UX-09

**Chosen direction: warm neutral with deep teal.** Neutral surfaces leave speech and state as the focus. Teal identifies primary actions consistently. Warm paper removes some visual glare without sacrificing contrast. Warning/error colours are reserved for actual conditions, not decorative activity. This is a considered starting choice, not a scientifically best colour for every person. No human avatar or romantic presentation is implied.

Light: paper `#F7F6F2`, white cards `#FFFFFF`, primary `#166354`, text `#20342E`, secondary text `#52635D`. Dark: background `#111B18`, cards `#1B2923`, primary `#98D2B8`, text `#EDF3ED`, secondary `#B8C8BE`. The app defaults to system appearance. Prototype starts light for review; its theme switch previews dark/system. Full semantic tokens are supplied in JSON; use roles, never ad hoc screen colours.

Typography uses system fonts (SF Pro/Android system) without remote font requests. Titles32, section24, body16, secondary14, captions12 logical units, with native scaling. Text hierarchy uses size/weight/spacing; meaningful information is not caption-only. Text containers grow/wrap; no fixed-height sentence boxes. Spacing uses4/8/12/16/20/24/32/40/48 units; controls and cards have consistent rounded corners.

Components: one dominant primary button; outlined secondary button; destructive confirmation button only in its sheet; text action with a48-unit hit region; labelled switch; whole-row radio choice; labelled dropdown; state pill with explicit text; full-width actionable notice; fact/history card; persistent three-destination navigation; native authentication/permission surfaces. A static decorative wave conveys brand, not actual microphone samples; it is excluded from accessibility semantics. It must not simulate listening while capture is stopped.

## 7 Accessibility and platform behaviour — VC-UX-10

Use WCAG2.2 AA design benchmarks: normal text≥4.5:1; essential control boundaries/icons≥3:1. Shared touch targets≥48 logical units with8-unit separation exceed the web minimum. Native iOS/Android rendering and accessibility sizes still need device checks. Text accompanies all states and semantic colours. Native VoiceOver/TalkBack labels announce action and state, not decorative waves; active-state announcements are concise and non-repetitive. No audio-only instruction or gesture-only destructive action.

Support keyboard focus, screen-reader order, native Dynamic Type/font scaling, contrast settings and reduced motion. No looping/pulsing animation is needed. Voice-only does not remove accessible visible Start/Stop, retry, volume and help. Lock clears private views and open sheets before showing generic content. Cancel retains prior setting/value. Changes to history/private/background consent are explicit and authenticated outside first-use onboarding.

Android uses its microphone foreground-service notification and real runtime permission flow. iOS uses its real permission/authentication sheets and permitted audio state. Do not copy Android notification controls into an iOS promise: the lock preview is annotated illustrative. Android Back and iOS back/sheet dismissal respect unsaved choices; cancellations never grant consent. Insets, Dynamic Type and platform accessibility semantics are native implementation tasks.

## 8 Prototype and review — VC-UX-11 to VC-UX-13

Open `Companion_Prototype.html`. Explore first-use setup, Start/permission, wake/turn/interruption, Memory authentication/correction/source deletion, settings/private mode, dark appearance and the lock policy. The simulation controls are outside the product frame. All sample conversations/facts are synthetic. No real microphone/audio/cloud/localStorage/database is used.

A design heuristic walkthrough is documented separately. It is not evidence from recruited users. Real usability review, screen-reader/device behaviour and product feasibility remain pending. Any revised design reference should carry its version so Codex does not implement an obsolete screen.

## 9 Handoff and approval — VC-UX-14

Use this document plus tokens and prototype for the product-screen tasks. Native controller state remains authoritative. The design describes visual/interaction intent and must not weaken the privacy, key, backup, retention, quota or background architecture. App code has not started in this task.

Owner review should cover: navigation, voice states, explicit consent, Start/Stop visibility, private mode, authentication, source deletion, background/lock limits and chosen theme. A package ready for review is not yet approved. Required user/device research and missing native verification must stay recorded; no automatic pass or blanket deployment authorization.

Sources consulted2October2026:
- W3C contrast: https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- W3C target size: https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- Apple accessibility: https://developer.apple.com/design/human-interface-guidelines/accessibility
- Android mobile accessibility: https://developer.android.com/design/ui/mobile/guides/foundations/accessibility
- Approved project specification, architecture and alternate-selection records.



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

## Revised design authority

Use Eilo_Visual_Interaction_Design.md and Companion_Design_Tokens.json v2.0 for changed Home/theme/results/surfaces. Old interactive prototype1.2 remains a historical interaction reference for untouched onboarding/Memory/account patterns; do not implement its teal Home or treat it as new visual evidence. Old22 colour-pair pass does not apply to v2.0. Generated concept controls are illustrative; accessible three-destination navigation and independent Voice only mode govern implementation.
