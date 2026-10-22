# S16 physical surface acceptance inventory

This standard-library-only tool checks inventory structure, required case coverage and aggregate artifact checksums. It does not operate a phone, grant permissions, inspect packets or prove evidence authenticity, observation quality, consent or privacy. An owner must review the underlying physical observations and aggregate artifacts. A fabricated manifest or copied approval flag cannot establish acceptance.

Run from `Eilo`:

```
python3 -m unittest discover -s packages/surface-acceptance -p 'test_*.py'
python3 -O -m unittest discover -s packages/surface-acceptance -p 'test_*.py'
python3 packages/surface-acceptance/acceptance.py packages/surface-acceptance/matrix.json
```

The committed matrix intentionally has no approved devices or results and returns HOLD. Add `--require-ready` for a review-inventory gate: HOLD exits 2, malformed evidence exits 1. Ordinary validation exits 0 for a well-formed HOLD inventory, so CI can verify preparation without pretending a physical pass. READY_FOR_MANUAL_ACCEPTANCE_REVIEW never changes S08 or authorizes memory, releases, distribution, network requests or feature activation.

## Collection prerequisites

Use the dependency audit and task states in `docs/sprints/S16_PREFLIGHT.json`. Obtain an owner-approved supported physical-device matrix and accepted native adapter/background eligibility first. Do not infer today's connected iPhone state from earlier trials. Confirm the specific test installation and any necessary notification/special-access prompt with the operator; never change another app's settings. Use synthetic content with a short-lived marker. No personal audio or conversation history is needed. No provider query, media download or network capture is authorized by this plan.

For each approved physical device, use an alias (never a UDID/serial), model family, OS version and the SHA256 of the exact installed build artifact. Run every applicable case below. Record PASS/FAIL, or NOT_RUN/BLOCKED with null evidence. UNSUPPORTED needs reviewed device evidence and keeps the matrix HOLD; removing a device or accepting a restricted support profile is a separate owner decision, not an automatic waiver. The tool requires an aggregate artifact for each observed case, current build hash, owner review and checksum; pending rows must have no evidence. Files must be bounded non-symlink JSON under `evidence/`, one file per device/case. Evidence contents are deliberately not echoed or auto-certified; review them for privacy and meaningful observations before inclusion. The manifest schema has no free-text content, account, endpoint or serial field.

## Physical journeys

| Case | Required observation |
| --- | --- |
| foreground | Current synthetic result, correct attribution and recoverable spoken text; navigation and native Stop accessible. |
| consent-denied-revoked | Display off initially; deny/revoke separately for notification/overlay and app display choice. No app auto-open or permission loop. |
| locked-content-redaction | Lock before/during/after schedule/render. No reply/query/source/image/history in any outside-app payload, visible surface or snapshot. Generic copy remains safe across races. |
| stop-new-query-stale-callback | Stop, new query and privacy epoch invalidate pinned/current cards and late async callbacks; no reopening. |
| expiry-pin-accessibility-focus | 19.9/20-second boundary, interaction/loading/speech/focus reset behavior, pin/close; notification duration is system-controlled. |
| screen-reader-large-text-reduced-motion | Actual VoiceOver/TalkBack, largest supported text, contrast, focus, native Back/safe areas, reduced motion. |
| media-denied-and-explicit-resume | Denied media keeps voice/text usable. When a permitted native player exists: explicit tap, listening/speech pause before play and explicit resume after failure/completion. No autoplay or media microphone ingestion. |
| termination-relaunch-no-auto-resume | Kill/service termination/relaunch drops stale content, remains truthful and never silently restarts capture, speech, search or result display. |
| notification-generic-payload-and-explicit-open (iOS) | Inspect all pending/delivered fields/actions/attachments/userInfo and notification-center/paired surfaces using synthetic markers; only generic operational copy, explicit tap opens app without restoring unauthorized work. |
| notification-focus-settings-system-timing (iOS) | Denied/provisional/authorized, revoked settings, Focus, unlocked/locked/terminated app; document actual delivery and absence of timing guarantees. |
| overlay-touch-back-insets-native-stop (Android) | Bounded card, move/pin/close/source, native Stop, underlying-app touch routing, gesture/keyboard insets and Back; no full-screen takeover. |
| overlay-blocking-app-and-oem-lifecycle (Android) | Special access deny/revoke, overlay-blocking activity and each supported OEM's background/service termination; safe fallback without auto-open. |
| independent-mic-background-display-consent | Cross product of mic/background/display grants and lock/active session. Display consent alone never starts/authorizes audio or bypasses platform background limits. |
| search-declined-confirmed-minimized-egress | Only after approved native provider/transport: denied/cancelled sends nothing, confirmed sends only approved minimized query/media types; current session cancellation and logging/storage behavior verified. |
| storage-cache-snapshot-privacy | Inspect payloads, OS/app notifications/caches/logs/snapshots/storage/backup using synthetic markers, plus native transition observations. Text search alone does not establish encryption or erasure. |

Do not substitute fixture tests, process-only simulator launches, a build success or historical model trials for these observations. Failed privacy stays a release blocker. Media/search prerequisites can leave a case BLOCKED; a denied-media fixture alone does not complete that case.
