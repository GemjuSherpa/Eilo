# S07 — VC-JOIN-02 spoken follow-up session

14 October 2026. Prepared for Gemju Sherpa review; physical acceptance remains partial.

Controller-owned volatile dialogue retains at most four completed user/reply pairs and 8192 aggregate UTF-8 bytes; each turn is at most4096 bytes per side. Only successful speech SDK completion commits a pair; unfinished/failed/interrupted replies are excluded. Stop/privacy/end/60-second actual conversational idle clear references immediately, before external cleanup effects. This is current-session context, not durable history, factual memory or proof of user hearing. String/vendor allocator retention remains unverified.

A current active post-reply session accepts native follow-up input without another wake event, while respecting token/permission/model and playback-tail gates. New/stale/ended sessions cannot use the follow-up seam. Actual loaded-model PromptBudget still drops oldest context as necessary without trimming fixed rules or the latest request.

Validation PASS: 213 Swift / 263 Android tests; strict Swift compilation; Android lint/normal Debug build/Release Kotlin compile; same iPhone 18 Pro app build/install/three fresh ten-second launches. Four focused tests per platform exercise two-turn context, initial/stale/tail denial, idle/end/Stop/privacy clearing, bounded pairs and overlap-safe WakeQuestionHandoff→StreamingAsr→one approved reply.

The updated explicit real simulator evaluation passes two native ASR→signed CPU→approved SDK spoken turns, with one initial real wake activation and no second wake. It exercises buffered suffix delivery using a scripted question-start marker, verifies completed context for the second prompt and verifies end closes the active session. Evidence/reproduction: `packages/conversation-integration/tests/ios-joined-results.json` and README. Default app activation remains unavailable.

Not run: natural combined wake/question endpoint calibration, microphone/VAD/echo wiring, physical airplane-mode/traffic, acoustic latency/intelligibility, Android real joined execution and production app/trust/framework embedding. Synthetic confidence and voice proof remain explicitly test-only. No full physical or release acceptance is claimed.
