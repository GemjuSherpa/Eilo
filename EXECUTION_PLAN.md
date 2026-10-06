<!-- Current authorization: Gemju Sherpa explicitly authorized S05 on 7 October 2026, with the ongoing task-to-sprint-to-main PR workflow. Current task VC-TURN-01; stop for review. No deployment or paid services. -->
# Eilo — Small-Task Execution and Review

Version 1.0 | 5 October 2026

## Latest Gemju Sherpa workflow

Gemju Sherpa reviewed and merged S04 and explicitly authorized S05. Use sprint/s05-turn-recognition and a separate task branch for each task. Implement VC-TURN-01 first, test it, commit/push and merge the task branch into the sprint branch, then open a PR to main and stop for review. Ongoing Git authorization applies to the remaining project tasks. Main merge follows review approval; no provisioning or release action is authorized.

## This is a plan, not execution permission
S01 is merged; S02 and S03 are approved by Gemju Sherpa. S03's distribution-hosting privacy gate remains blocked: review approval does not establish infrastructure evidence. S04 is reviewed and merged; its three physical/background blockers remain. S05 is selected. All detailed baseline IDs/dependencies remain authoritative. Do not renumber tasks or execute this entire document in one turn.

## Stage 0 — historical context intake
Read the root context and baseline documents. Acknowledge the product/data boundaries, candidates versus measured evidence, missing artifact/toolchain/device constraints and assumptions. Wait. The next task candidate is VC-DEVOPS-01 repository/board baseline, only after an explicit Gemju Sherpa instruction with target repo/environment. Repository creation, initialization or board mutation is not authorized now.

## Stage 1 — scaffolding, split into independent changes
After authorization, select the relevant existing BASE/DEVOPS task and verify dependencies. Proposed atomic sequence: (a) repository/folder and package-manager baseline; (b) strict TypeScript, lint/format and test commands; (c) clean Android native build; (d) clean iOS native build; (e) synthetic native module contract/build. Each is separately reviewed. Create only the assigned boilerplate/configuration; do not build product features, register cloud services or bundle unlicensed models.

Acceptance: actual local supported build/run and lint/typecheck evidence for the assigned platform. Document absent macOS/Xcode/Android SDK/device capability. A web preview does not verify a native app. New Architecture/custom native build is required; Expo Go is not sufficient. Review between atomic tasks.

## Stage 2 — schemas and contracts before backend behavior
Separate contracts from migrations and hosted deployment. First define account lifecycle and safe typed DTOs/error schemas plus native controller/event contracts with synthetic fixtures. Then propose minimal Neon data mapping and Better Auth-compatible auth migrations/Drizzle profile migration responsibility. Review no-history/query/location server fields, authorization and deletion semantics.

Test migration application/rollback or forward recovery on disposable synthetic local databases where authorized. This does not authorize provisioning Neon or touching staging/production. Mock endpoints are plainly labelled and do not count as provider/auth integration passes. Search contract/provider selection is a separate dependency-gated task, not a reason to send live queries during account setup.

## Stage 3 — critical feasibility before full product polish
Follow backlog dependency order, splitting audio capture/controller, wake/VAD, ASR, LLM, offline TTS, interrupt/epoch control, native lifecycle and protected storage into separate reviewed tasks. Measure the full pipeline on phones. Locked history sealing and iOS screen-off execution are critical gates, not assumptions to defer past release.

Minimal synthetic experiment controls are permitted only in their authorized feasibility tasks. Do not implement a large UI or assume model viability from desktop benchmarks. If a gate fails, report the evidence and request a reviewed requirement/platform change instead of expanding cloud processing.

## Stage 4 — atomic product features
Examples, each with its own backlog ID and dependencies: permission explanation; foreground Start/Stop state; Reduced Motion ripple; progressive spoken text; one display preference; expiry timer; authenticated Memory view; retention/delete-one; email sign-in; one social redirect flow. Separate UI behavior, native bridge/service and integration where independently reviewable. Preserve dependency edges; never treat this list as a rigid replacement order.

UI follows Design 2.0, not old teal prototypes. Auth cannot gate guest/offline conversation. Search/media/native surfaces come later after consent/provider/security feasibility and specific feature approvals. Search gateway, query confirmation, safe result normalization and cache inspection are distinct tasks.

## Stage 5 — integration, staging and release, all separate approvals
Integrated native/device regression, privacy/security/provider licensing, accessibility and limited pilot evidence precede staging. Reviews tested concrete candidates. Staging authorization is separate from a feature approval; production/backend/store publication are separate decisions. GitHub Actions checks do not replace Gemju Sherpa review or manufacture private-plan enforcement. Git actions follow the latest explicitly scoped Gemju Sherpa authorization; tests do not provide release permission.

## Per-task procedure
1. Select one explicitly authorized ID; inspect dependency approval/evidence and relevant files. State scope and objective. If too large for a reviewable diff, propose a documented split preserving parent ID linkage.
2. Implement only that responsibility. Keep unaffected human changes intact. Do not add future placeholders, unrelated packages/refactors or speculative features.
3. Immediately run relevant lint/compiler checks after producing code, then focused tests/native validations appropriate to behavior. Resolve relevant failures within scope; report missing environments honestly.
4. Update existing task tracker with implementation/evidence/checks and awaiting-review status. Do not record approval from Gemju Sherpa before receiving it. Schema extensions/new subtask IDs require explicit mapping, not replacement of stable IDs.
5. Provide the review summary below and stop. Gemju Sherpa reviews the PR and approves subsequent work; scoped task commits/pushes and task-to-sprint merges are authorized.

## Review response template
- Task and requirement IDs:
- Result and observable behavior:
- Files changed and why:
- Actual checks (command/environment/result):
- Not-run/blocked checks and reason:
- Evidence and reproduction steps (synthetic only):
- Material risks or limitations:
- Tracker state: awaiting review / blocked:
- Next suggested task (not executed):
- Source control: task/sprint branch names, actual commits and PR, with main merge awaiting review.

## Completion rule
A written implementation is not a passed test; a passed test is not approval from Gemju Sherpa; feature approval from Gemju Sherpa is not release authorization. Keep these states separate. A task with missing mandatory native/security evidence may be reviewable as a partial result but cannot be marked fully verified/release-ready.
