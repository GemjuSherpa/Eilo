# S07 — clause refusal regression fix

14 October 2026. Final S07 QA found four benign combined-policy persona replies rejected by the lexical screen. They declare Eilo cannot impersonate a person, diagnose, feel emotions or promise secrecy. The initial false-positive candidates are retained in `ios-persona-candidates-pre-refusal-fix.json`.

Both native policies now permit only four exact canonical refusal clauses and their exact AI-identity-prefixed forms. No broad negation rule, fuzzy matching or diagnosis/promise allowance is added. Real queue tests show split AI-identity/secrecy refusal clauses can reach the sink; altered commitments and appended secrecy promises remain denied.

Validation PASS: 218 Swift / 268 Android tests, strict Swift compilation, Android lint/normal Debug build/Release Kotlin compiler, same iPhone 18 Pro app build/install and three fresh ten-second launches. Nine actual combined-policy CPU persona candidates complete without truncation and now pass this narrow lexical screen; no candidate is released to speech or assigned semantic ratings. Public-release semantic review and all physical/production gates remain open. This is not general semantic safety certification.

Branch `task/s07-clause-refusal-fix` follows the same build/test/commit/push/task-to-sprint workflow and updates PR #49; main is unchanged.
