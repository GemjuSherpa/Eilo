# Eilo — AI Coding Instructions

## Current task boundary
The owner explicitly authorized S01 implementation and testing. Create a separate branch before each authorized sprint; complete the selected sprint and stop for human review. No future sprint, provisioning, deployment or publication is authorized. The human verifies, commits and pushes.

## Read before an authorized change
Read AGENTS.md, PRD.md, ARCHITECTURE.md, COMPLIANCE_AND_SECURITY.md, EXECUTION_PLAN.md and the selected task plus dependencies in docs/baseline/Voice_Companion_Feature_Backlog_v1.0.json. Read relevant design tokens/contracts and actual repository instructions. New owner instructions prevail. Stop and report a material scope/privacy conflict rather than silently weaken the specification.

## Code conventions
- TypeScript strict mode, no implicit any or unchecked casts to bypass DTO validation. Use unknown and narrow untrusted data. Use strict null handling; document intentional exceptions with evidence.
- Functional React components and hooks, named domain-oriented functions, explicit module boundaries. Components do one job; separate native/services/domain/view responsibilities. Small reviewable diffs, no unrelated refactors.
- Use StyleSheet and semantic token roles. No hard-coded alternate palettes or parallel CSS systems. Native accessibility labels, truthful audio states, text scaling, 48-unit targets and Reduced Motion are part of behavior.
- Zustand holds non-sensitive UI state only. Native audio/privacy state has one source of truth. Local component state is acceptable for isolated interactions; Context only for scoped dependency injection, not a second mutable global store. No Redux/MobX/Jotai, duplicate controller states, persisted query caches or conversation data in JS storage.
- Use ESLint and Prettier. Avoid blanket lint disable, @ts-ignore, ts-nocheck, expect-any test escapes or disabling security checks to get green output. Use runtime validation for external schemas. Pin compatible dependency versions through the reviewed lockfile.
- Keep keys/tokens/raw audio/native histories out of JS wherever the architecture requires. Never log personal values. No cloud inference, generic tracking SDK or real user test data.

## Errors, async work and cancellation
Each API/network operation must have an explicit try/catch at its boundary (or a shared typed adapter that owns that boundary), deadline/cancellation handling, validated response/error mapping and safe user-facing feedback. Never silently swallow an exception, show success on failure or retry consented searches without renewed deliberate action. Avoid repetitive nested catches that lose the cause.

Implement a central typed ErrorService during its separately authorized task. It accepts allowlisted codes/component/severity/random operation IDs only—no exception message/stack/body/user input unless proven sanitized. Local safe status logging is sufficient; no hosted telemetry vendor is implied. Distinguish offline, denial, timeout, cancellation, auth expiry, quota, invalid response and unexpected failure. Expected cancellation is not a user error. Raw causes must not be exported, persisted or printed.

React render error boundaries isolate screen failures and provide recovery; they do not catch async handlers/native errors. Handle these through the controller/service contracts. Never keep sensitive UI visible in fallback screens. Match generation/session/privacy epochs before committing any callback. Preserve offline core during optional service failures.

## Verification after code changes
After each code-producing change, run the relevant package lint and compiler/typecheck immediately. Once scaffolding defines commands, use npm run lint and npm run typecheck for affected workspaces, plus appropriate native compiler/lint checks for Kotlin/Swift/C++. Do not pretend tsc validates native C++ or a simulator proves screen-off behavior. Initially scaffolding must establish these scripts before its review gate.

Run meaningful focused tests for changed behavior/security boundaries; use synthetic data. Validate native integration on the required environment/devices when a task needs it. If dependencies/toolchains/devices are missing, state NOT RUN/BLOCKED and the exact reason. Do not bypass gates, fabricate output or mark a task fully verified. Documentation-only changes require link/consistency checks, not unnecessary app builds.

## Human review — mandatory
Complete dependency-ready tasks within the explicitly selected sprint, in small verifiable changes. Produce a review summary: task/requirement IDs; behavior before/after; changed files; checks with actual commands/results; unrun tests; evidence; risks/limitations; suggested next task. Update tracker truthfully to awaiting human review. Then stop. Do not interpret silence or success as approval to continue. Human review of one task does not authorize the whole roadmap.

## Source-control and release rules — explicit owner instruction
DO NOT commit anything. Do not stage (git add), push, merge, create tags or rewrite history. The human verifies, stages, commits and merges. Read-only git diff/status/log are allowed. Do not discard/revert the human's changes, force-push or alter remotes. Leave changes in the working tree for review.

No PR publication, staging deployment, production deployment, remote migration, store upload, provider setup or messages to people unless separately explicitly authorized. If staging/deployment is later authorized, prepare and test the concrete candidate before the human gate. Never treat a configuration plan as permission to create external resources or incur costs.
