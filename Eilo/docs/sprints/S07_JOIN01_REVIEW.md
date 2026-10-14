# S07 — VC-JOIN-01 one generic spoken turn

14 October 2026. Prepared for Gemju Sherpa review; acceptance remains partial.

GenericSpokenTurn now joins final native ASR input to uncertainty/fixed danger/capability routing, loaded-tokenizer PromptBudget, signed controller-owned CPU generation, non-thinking output validation and per-clause speech approval/queueing. Final submission is one-shot and token bound. Default configuration/adapter/readiness remain unavailable. No conversation persistence, personal-memory retrieval, tool actions or content bridge exists.

Local validation PASS: 209 Swift / 259 Android tests, strict Swift compilation, Android lint/normal Debug build/Release Kotlin compilation and same iPhone 18 Pro app build/install/three fresh ten-second launches. Four focused tests per platform cover final-once, fixed/uncertain bypass, failure gates and late output after Stop.

Actual joined iPhone 18 Pro ARM64 simulator evaluation PASS: real sherpa wake activation, Moonshine streaming ASR final, temporary signed Q4 pack/controller-owned worker with actual tokenizer budgeting, configured clauses and installed AVSpeech SDK completion. The first monolithic link failed on 118 duplicate vendor symbols; the verified four-export ASR dynamic-library isolation fixes simulator coexistence without changing vendor archives or suppressing errors. The initial failure is retained in a JSON record. See `packages/conversation-integration/tests/ios-joined-results.json` and that package's README for reproduction and Apple references.

Not run: physical airplane-mode/traffic capture, calibrated ASR confidence, actual VAD/capture/echo integration, acoustic timing/intelligibility, Android real joined execution and production framework embedding/signing/trust/app caller. Simulator uses supplied synthetic confidence and scripted fixture endpoint, plus synthetic exact-voice/OS evidence. SDK completion is not proof that a user heard speech. Separate frozen wake/question files are used here; combined suffix handoff follows in JOIN02. No release readiness or complete end-to-end physical acceptance is claimed.
