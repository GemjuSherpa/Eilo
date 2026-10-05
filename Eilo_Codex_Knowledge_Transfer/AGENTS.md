# Eilo App — Codex knowledge handoff

## Current authorization — highest priority
The owner requested transfer of project knowledge only. DO NOT start project setup, create a repository, install dependencies, scaffold React Native, implement features, run development experiments, provision services, deploy or publish. Read and acknowledge the context, then wait for explicit authorization of the next small task. Document approval is not implementation approval.

## Reading order
1. Eilo_Project_Management_Plan.md (all sections, especially 17 change record, 23 checklist coverage and 24 assumptions).
2. Eilo_Visual_Interaction_Design.md — current Design 2.0 behavior.
3. Voice_Companion_MVP_Spec_v1.0.md and Voice_Companion_Architecture_v1.0.md — current amendments take precedence over historical bodies.
4. Companion_Design_Handoff.md, Companion_Design_Review.md and Companion_Design_Tokens.json.
5. Voice_Companion_Feature_Backlog_v1.0.json — authoritative version 1.5 requirements/task states/dependencies, plus Markdown and CSV execution tracker.
6. Voice_Companion_Implementation_Plan_v1.0.md and Eilo_DevOps_Recommendation.md.

## Conversation decisions and intent
Eilo is a friendly voice-first consumer companion; tagline: “I am here for you”. The owner explored Siri/Alexa alternatives, emotionally responsive conversation, low latency, a free core service and on-device inference to avoid per-minute cloud inference costs at scale. English first, React Native cross-platform candidate. Do not assume inference feasibility or emotional understanding has been demonstrated.

The initial guest-only direction was superseded by optional accounts: email/password plus Google and Apple where required, with a separately hosted Better Auth service and Neon PostgreSQL for minimal account information. Guest/offline conversation remains core. Neon-managed authentication compatibility was not demonstrated.

Privacy is the highest priority. Local encrypted consented history and derived memory, no cloud conversation/location history or raw-audio storage. Local history policy, private sessions, lock handling, retention/quota and key lifecycle are defined in the specifications. Optional live search is a newly confirmed-query exception: no whole transcripts, history, account identity, raw audio, GPS or personal model uploads. Provider processing and retention still require review. No claim that the entire app is offline when optional online features are used.

Screen-off listening is desired but separately consented and unproven. Native OS restrictions matter. Generic locked surfaces; no sensitive content on lock or unauthorized displays. Calls, camera, unrestricted app control, location, personal model training and cloud aggregation were discussed as future goals, not authorized MVP features. Future tuning must get its own feasibility, security and consent specification.

The originally separate ripple design experiment is now explicitly merged by the owner. Blue/light-purple centre-out rounded waves; native iOS/Android navigation; essential Start/Stop/Memory/Settings remain accessible. Optional text/images/videos accompany speech. With no rich result, progressively display spoken-response text. Inside app: cards. Outside app: permissioned Android overlay subject to feasibility; iOS generic permitted notification fallback, not arbitrary Siri-like overlay. Inactivity dismissal and Keep visible behavior are specified. Concept images and one-second animation are illustrative, not implemented or tested native screens.

GitHub is confirmed public initially, private later. Actions recommended; EAS Build/Submit, Vercel small account backend/website, Neon and TestFlight/Play staging are planned candidates. Docker optional; it does not supply the iOS toolchain. No infrastructure is configured by this transfer. Never expose secrets or user data in public history.

## Implementation workflow when separately authorized
One dependency-ready, single-responsibility task at a time. Explain scope, implement the smallest reviewable change, run relevant meaningful checks, update tracker/evidence, present result and wait for owner review before the next task. Human approval before staging, deployment and publication. Do not dump a full application or mark unrun checks passed. There are 175 stable tasks in 23 groups; 26 new visual/search/surface/DevOps tasks remain planned. Approval of prior UX is design acceptance only, not native-device test evidence.

## Evidence and assumptions
No application implementation or physical-device pass has been established. Prior prototype/synthetic checks are historical and do not validate Design 2.0. Model conversion/packaging, native integration, latency/RAM/battery, background support, lock encryption composition, accessibility, provider contracts and licensing remain gates. Hardware verification was explicitly deferred to development. Do not repeat expensive verification until the owner authorizes the relevant task.

The latest 27-page plan follows all 29 items in the attached five-phase checklist. Section 24 marks assumptions: Australia-first adult English pilot; founder 20 hours/week; indicative 18 working weeks/360 hours; AUD6,360 cash allowance including contingency, not spending approval; provisional Android15+/iOS18+/8 GB test devices; text on/media off/search off with each query confirmed; 20-second idle expiry; explicit video play pauses speech/listening with manual resume; pilot recruitment and metadata retention remain assumptions. These values are not user-confirmed commitments.

## Provenance and boundaries
This handoff consolidates the visible Eilo conversation decisions and the current supplied project documents. It is not a verbatim chat export; unseen intermediate exchanges and artifacts cannot be reconstructed. The package contains the current source baseline, detailed requirements, dependency graph, risks, assumptions and illustrative references. If a required historical artifact is referenced but absent, report it as missing instead of inventing its contents. Ignore unrelated personal/workplace memories; they are not Eilo requirements.

## First response in Eilo App
Acknowledge that you have read the package, summarize the baseline and unresolved gates, and state that setup/development remains paused. Do not execute VC-DEVOPS-01 until the owner explicitly asks.
