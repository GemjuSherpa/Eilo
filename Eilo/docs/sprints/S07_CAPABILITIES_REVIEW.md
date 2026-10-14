# S07 — VC-BEHAV-02 capability boundaries

14 October 2026. Prepared for Gemju Sherpa review in the final S07 PR.

Unsupported English live-news, call/photo/app-control and diagnosis requests now have fixed native replies explaining limits. No network, phone-action, location or permission interfaces are present in this policy. The fixed Qwen system turn also requires uncertainty/clarification and forbids claiming these capabilities. User text cannot replace the system role. Normal model readiness remains gated.

Validation: 198 Swift tests including three focused capability tests PASS; strict Swift source compilation PASS. Android unit tests, lint, normal Debug build and Release Kotlin compilation PASS. Three pinned official Qwen non-thinking template goldens PASS. Same iPhone 18 Pro simulator normal app build/install and three fresh ten-second launches PASS (see local capabilities proof).

Reproduce: run `swift build -Xswiftc -warnings-as-errors` and `swift test` in `packages/native-test-seam`; run Gradle `:app:testDebugUnitTest :app:lintDebug :app:assembleDebug :app:compileReleaseKotlin` with the existing JDK17/Android SDK; run `packages/llm-runtime/check_template.py` using the existing model-build environment and pinned tokenizer config. No dependency installation or model download is required.

Limits: narrow English routing may overmatch quotations/negations and miss paraphrases; it is not a semantic classifier or professional advice. A fixed reply is safer than attempting an action; no tool can be invoked here. New model-generated capability candidates and physical-device trials are not run in this checkpoint. Speech approval and joined callers follow in S07. No release acceptance is claimed.
