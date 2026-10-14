# S07 — VC-BEHAV-04 pre-speech clause policy

14 October 2026. Prepared for Gemju Sherpa review.

Each native clause now has an explicit configured policy, denied by default, bound to the exact controller token, state, permission/model readiness, speaker confirmation and privacy epoch. NativeClauseQueue checks it on enqueue and again at drain, then rechecks cancellation after the policy callback before scheduling the sink. Reentrant Stop can no longer publish a late clause or retain it in the queue.

The bounded English screen rejects control/hidden/non-English characters, dangerous/action/diagnostic/secrecy/exclusivity/human-identity vocabulary and selected promises. Exact frozen native capability/danger/clarification/identity/goodbye replies are permitted without granting tool access. This is a lexical screen, not a complete semantic classifier: paraphrases may evade it, benign phrases may be rejected, and claims split across clauses may evade semantic checks. Review/quality evaluation and physical tests remain release gates. No small-model safety certification is claimed.

Validation: 205 Swift tests / 255 Android tests, strict Swift compilation, Android lint/normal Debug build/Release Kotlin compilation PASS. Four focused tests on each platform exercise unsafe/no-playback, default denial, fixed replies, modified-response rejection, privacy invalidation, queued revalidation and reentrant Stop during both policy calls. Same iPhone 18 Pro app build/install and three fresh ten-second launches PASS. An initial Kotlin compile attempt exposed private controller API references; those were replaced with a scoped native pre-speech revalidation method and checks rerun successfully.

Reproduce using the existing native commands in S07_CAPABILITIES_REVIEW.md. Actual generated speech and acoustic/device cancellation latency were not run here; the joined pipeline follows next. Ordinary model readiness remains unavailable.
