# S07 — VC-BEHAV-03 imminent-danger response

14 October 2026. Exact wording and scenarios await Gemju Sherpa review before public release.

Native conservative English signals select one frozen supportive response before model generation. It directs a person in immediate danger to local emergency services and trusted nearby help; the Australian number is explicitly conditional. No location, monitoring, emergency-action, contact or permission interfaces exist. The fixed system prompt requires the same boundary.

The response and review rubric are in `packages/persona-policy/tests/danger-fixtures.json`. Guidance source checked 14 October 2026: [Healthdirect](https://www.healthdirect.gov.au/are-you-experiencing-suicidal-thoughts). This implementation paraphrases its immediate-danger and trusted-support guidance; it is not clinical risk assessment.

Validation: 201 Swift tests including three focused danger tests; strict Swift compilation; Android unit tests/lint/normal Debug build/Release Kotlin compilation; three pinned official non-thinking template goldens; same iPhone 18 Pro simulator normal app build/install and three fresh ten-second launches PASS. Reproduce using the existing native package/Gradle/template commands in S07_CAPABILITIES_REVIEW.md. Fixture tests bind both platforms to identical wording and prove user instructions cannot suppress matched signals.

Limits: English phrase detection can miss paraphrases and can overmatch fictional, historical or negated statements. Such matches receive conditional guidance rather than a diagnosis. No classifier sensitivity, acoustic recognition, physical-device voice success or public-release approval is claimed. Ordinary model readiness remains denied. Speech approval and joined integration follow separately.
