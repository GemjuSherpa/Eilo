# S07 — Safe generic conversation integration

14 October 2026. Remaining six implementation tasks prepared for Gemju Sherpa review. No main merge or public release is performed. Persona policy PR #48 is already merged; the same Git permission applies throughout this sprint.

| Task | Result | Evidence |
|---|---|---|
| VC-BEHAV-01 | Prior persona implementation merged in PR #48; combined-policy regression candidates remain for semantic review | S07_PERSONA_POLICY_REVIEW.md; persona-policy/tests |
| VC-BEHAV-02 | Fixed native capability limits and privileged uncertainty rules | S07_CAPABILITIES_REVIEW.md |
| VC-BEHAV-03 | Frozen supportive danger response and wording rubric; no location/emergency action | S07_DANGER_REVIEW.md |
| VC-BEHAV-04 | Default-denied per-clause screen, revalidation and post-policy Stop race fix | S07_CLAUSE_REVIEW.md |
| VC-JOIN-01 | Native final-ASR→signed budgeted CPU→approved SDK speech seam and real simulator evaluation | S07_JOIN01_REVIEW.md |
| VC-JOIN-02 | Bounded completed volatile context, follow-up, idle/end/Stop/privacy clearing and suffix handoff | S07_JOIN02_REVIEW.md |
| VC-JOIN-03 | Cancel-before-replace, exact-one input, separation lease and queued request cleanup | S07_JOIN03_REVIEW.md |

Separate task branches are committed/pushed and merged into `sprint/s07-conversation-completion`; its single PR targets main for review. Each code task has its own normal app build/install and three fresh ten-second iPhone 18 Pro launches before commit. Only scoped Xcode source entries are staged; personal signing/plist/S02 changes remain excluded. S07_VALIDATION.json records those local proofs.

Final local checks: 217 Swift and 267 Android tests; strict Swift compilation; Android lint/normal Debug build/Release Kotlin compiler; workspace lint/typecheck/9 mobile+33 contract tests; three official Qwen non-thinking template goldens. Actual simulator joined evaluation uses existing checksum-pinned assets, real wake/ASR/signed controller CPU/loaded tokenizer and speech SDK; follow-up and replacement complete. Synthetic state/confidence/endpoint/voice/separation inputs are explicit in the report. Nine combined-policy CPU persona candidates completed without truncation and are recorded for review; the lexical screen would reject four benign refusal/identity replies (false positives), illustrating its limited semantic ability. No candidate was released to speech. earlier candidates/failures are retained. No automatic semantic ratings or approval are assigned. Staged and new sprint-history secret scans are required before final publication.

The joined static link initially failed with 118 duplicated vendor runtime symbols. A four-export, TWOLEVEL native ASR dynamic library isolates the unchanged vendor archive and passes simulator coexistence. Production framework embedding/signing/device compatibility remains open. See the integration README and retained initial-link failure record.

S07 is **not fully accepted/release-ready**. Remaining gates: physical iPhone/Android airplane-mode and egress capture, actual microphone/VAD/echo/calibrated confidence/wake-boundary attachment, acoustic latency/first-audible/intelligibility, semantic danger/response review, Android real joined execution, production signed pack/license/trust/app caller and dynamic-framework embedding. The connected iPhone is offline; no physical Android is available. Normal Home still has the missing-model/readiness gate. This PR does not enable everyday spoken conversations or bypass any readiness gate. SDK completion does not prove user hearing; releasing references does not certify forensic memory erasure.

Reproduce native/workspace checks with the existing commands in task review records. Run `python3 packages/conversation-integration/check_ios.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8` and `python3 packages/persona-policy/check_ios.py --udid E01AE333-A393-48F6-AAD7-579F0A5DB1F8` from Eilo using existing local assets. Neither downloads dependencies nor opens a microphone. Do not close sprint issue #7 based on this partial acceptance evidence.
