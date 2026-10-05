# Eilo project management and DevOps recommendation

5 October 2026 · GitHub selected by owner, public initially/private later. Remaining stack recommended and feasibility gated; nothing configured/deployed. UX and visual scope decisions recorded separately.

## Recommended responsibilities

| Platform | Responsibility | Decision |
|---|---|---|
| GitHub repositories and Projects | Source, issues, dependencies, pull requests, evidence and owner decisions | Recommend |
| GitHub Actions | Fast checks, native compile checks, backend checks and manually triggered release orchestration | Recommend |
| EAS Build and Submit | React Native Android/iOS binary builds, signing and store uploads | Recommend, subject to native feasibility spike |
| TestFlight and Google Play test tracks | Mobile staging and release candidate distribution | Recommend |
| Vercel | Website and small Node.js account/auth API | Recommend, subject to Better Auth deployment validation |
| Neon PostgreSQL | Minimal identity/profile and authentication data | Previously authorized direction |
| Docker | Reproducible local backend/test environment when useful | Optional; no requirement for initial mobile development |

On-device conversation inference remains on the phone. Neither EAS nor Vercel serves conversation inference. EAS supports existing native React Native projects; use custom development builds and retain explicit control of Kotlin, Swift and C++ integration. Expo Go is insufficient for this project's custom native requirements. Docker does not replace the macOS/Xcode toolchain required for iOS builds.

Keep one repository initially: mobile app, account service, shared contracts, documentation and CI definitions. Do not add Kubernetes, a separate CD platform or orchestration machinery before a demonstrated need.

## Small tasks and review

One issue represents one independently testable responsibility. Include requirement IDs, explicit scope, dependencies, acceptance criteria, relevant tests, privacy implications and evidence links. Suggested board states: Backlog → Ready → In progress → Review → Approved → Staging → Released. Separate task completion from release membership: many approved tasks may ship together.

For each task: create a short branch, implement, run relevant checks, open a focused pull request, attach evidence, obtain owner review, then merge. Automated checks do not replace owner approval. Produce staging builds from a batch of approved tasks rather than building and publishing a store release for every small task.

For a release: record the approved commit, dependencies, build configuration, version, artifact identifier, test results and owner decision. Trigger staging distribution, test real phones, approve a release candidate, then authorize production backend deployment and store submission/release as separate actions. Store upload, store review and public publication are separate events.

For production mobile releases, build a candidate using production configuration from the approved commit and test that candidate through appropriate restricted distribution. A staging-configured binary is not byte-identical to a production-configured binary. Preserve the tested production candidate for store release where supported.

## Checks and feasibility gates

Fast CI: lint/type checks, focused unit and integration tests, dependency/license checks and secret detection. Native compile checks run when relevant native changes occur. Use Linux for suitable checks and Android builds; iOS compilation requires macOS. Schedule expensive builds around integration milestones.

First engineering spike must establish that EAS can compile, sign and distribute the C++ inference integration and native lifecycle services on both platforms. Test offline inference, model asset handling, foreground/background transitions, permissions, interruptions and lock-screen privacy on physical phones. Measure latency, memory, battery and thermal behavior. None of these are proven by the approved browser prototype.

Validate Better Auth with React Native, email/password, Google, Apple on iOS, deep links, secure session storage, callback configuration and Neon migrations. Confirm Vercel Node.js suitability, database connection handling, region placement and deletion/recovery jobs. Use a persistent Node.js hosting service if those requirements do not fit the validated Vercel setup.

If EAS does not fit native requirements or cost, retain GitHub Actions with Gradle for Android, Xcode on macOS for iOS, and fastlane for signing/distribution. This reduces reliance on EAS but increases maintenance of signing and build infrastructure.

## Environments and privacy

Separate development, staging and production credentials, database resources, auth callbacks and configuration. Use synthetic accounts in development and staging; never clone production identity records into preview databases. Keep database and provider secrets server-side, and mobile signing credentials in restricted CI secret storage.

Conversation history, derived personal memory, raw audio and location history stay out of the backend, logs, CI evidence and analytics. Sanitize crash reports and test recordings. Production account operations remain subject to the approved retention/deletion specification and outstanding release privacy assessment.

Maintain compatibility with older installed app versions. Use additive database/API changes and explicit migration review. Backend rollback cannot instantly roll back installed mobile apps; stage rollouts, preserve API compatibility and prepare a corrective binary. Native-code changes require a new binary. Defer OTA updates until an explicit runtime compatibility and approval policy exists.

## Approval enforcement and cost

GitHub documentation currently restricts environment required-reviewer rules to public repositories on Free, Pro and Team plans. Verify the selected private-repository plan before relying on that control. For a small owner-operated project, documented owner approval plus owner-controlled manual deployment/store release is a practical starting process, but is not equivalent to an independently enforced two-person gate. Choose Enterprise or another supported enforcement mechanism if independent technical approval enforcement is required.

Budget separately for developer store accounts, macOS CI time, EAS builds, backend hosting, Neon and any email delivery. A free app does not imply free development infrastructure. Avoid quoting a monthly estimate before build frequency, team size and backend usage are known.

## Immediate next step

Review this stack, then prepare the repository/board and a development readiness slice: reproducible native builds, on-device inference feasibility, auth integration feasibility and release-gate configuration. Do not start the full feature backlog until the platform constraints have evidence. This document recommends tools; it does not authorize account creation, spending or deployment.

## Official references

- https://docs.expo.dev/build/setup/
- https://docs.expo.dev/bare/overview/
- https://docs.expo.dev/deploy/submit-to-app-stores/
- https://docs.github.com/en/actions/reference/workflows-and-actions/deployments-and-environments
- https://vercel.com/docs/functions/runtimes/node-js

## Recorded GitHub decision and scope merge

Owner confirmed GitHub public initially and private later. Record migration as a planned security/process change; public exposure cannot be undone by later privacy. Never put credentials, personal test data, unapproved proprietary assets or restricted model weights in public Git history. Check licensing and plan-dependent branch/environment protection before repository setup and again before switching visibility. Actions PR jobs cannot access production secrets; restrict deployment authority to owner-approved trusted refs.4 DEVOPS tasks now track setup/checks/signing/release controls. The175-task baseline includes new visual/search/surface work; budget/provider gates remain open.
