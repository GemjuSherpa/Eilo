# S04 iOS lab lifecycle observations — 24 October 2026

Six ordered cases completed on iPhone 17 Pro Max (iPhone18,2), iOS 26.6.1/build23G83,
12,262,113,280 bytes RAM, with the operator reporting Airplane Mode and Wi-Fi/Bluetooth off.
The dedicated lab build uses the existing approved 0.6B assets, existing development profile
and Xcode 27.1. Installation preserved app data. No ordinary-app runtime was replaced.

| Case | Successful observation | Retained failures in final session |
| --- | --- | --- |
| Playback Stop | Active, stopped, delayed no-resumption check | 0 |
| Playback Home | Scene resigned, stopped, foreground return checked | 1 protected-data event; wrong action/event for Home |
| Playback lock | Protected data unavailable, stopped, foreground return checked | 0 |
| Quiet capture Stop | Active, stopped, delayed no-resumption check | 0 |
| Quiet capture Home | Scene resigned, stopped, foreground return checked | 0 |
| Quiet capture lock | Protected data unavailable, stopped, foreground return checked | 0 |

The final session retains seven rows: six OBSERVED and one FAILED. No failed attempt was
removed or promoted. Earlier separate sessions retain one successful playback Stop and two
lock failures. Those lock attempts stopped output, but the first harness rejected protected-data
unavailability arriving before scene resignation. The fix accepts that event only for requested
lock cases and still requires foreground return and delayed verification. Regression tests
cover this callback order, missing return, unexpected events, and no automatic resumption.

An earlier force quit was confirmed by the operator and explains a fresh process with disabled
setup controls; it is not evidence of an OS crash. The lab now archives prior metadata-only
reports byte-for-byte before a new process starts a fresh sequence. Reports keep their original
source revision and process session. No raw audio, transcript or model output is exported.

Evidence is under packages/physical-ios-trial/tests/ios-lifecycle-*.json. The provenance manifest
pins exact report bytes, source revisions, model hashes and unsigned/signed build receipts.
The physical evidence test is mandatory and checks all six final cases and the retained failure.

These are lab controller/SDK observations, not independent acoustic measurements, production
pipeline acceptance, a 300 ms stop result, forensic erasure proof, or support for locked capture.
All release-level physical gates, network attribution and acoustic timing remain NOT_RUN;
release HOLD and disabled memory remain unchanged. No keepalive/background entitlement is added.

The operator confirmed iPhone only: call/route fixtures, an independent recorder and physical
Android are unavailable. Active hardware permission revocation, accessibility, authentication,
reboot and sustained workload rows remain
unrun for this follow-up; broader S04 feasibility is not declared complete. The separate main
model-reply failure is still open: a host-only reproduction reached the lexical policy screen,
which does not establish the iPhone failure cause or justify weakening output guards.

Validation: Swift lifecycle/archive state probe, eight strict device/simulator source typechecks,
seven Python report tests in normal and optimized mode, unsigned build and existing-profile
codesign verification/install passed. Earlier unchanged normal-app Swift/simulator, JavaScript
and Android regressions remain recorded in the working checkpoint; GitHub checks must pass on
the final sprint head before authorized merge.

## OS permission boundary follow-up

The real OS adapter reported DENIED, native Start was rejected with permission_required,
and the closed lab adapter recorded zero capture-effect calls and no pending capture after
the foreground delay. After permission was restored, a different process reported GRANTED,
stopped, zero capture-effect calls and no Start request. The denied row remains unchanged in
the append-only ledger. These are two successful observations with no failed ledger rows.

The restored observation is a fresh-process no-start result, not survival of an earlier
controller. The probe intentionally cannot open hardware. Active hardware revocation remains
NOT_RUN; opening Settings already resigns the scene and stops capture. The earlier generic
“could not be preserved” message preceded a saved denial; the OS was subsequently observed
as granted, and the ledger deliberately rejects a granted-first restoration without prior
denial. Local regression verifies that prerequisite failure creates no report file. No storage
failure or permission-denial pass was inferred from the generic message.

Exact reports and source/build receipt are ios-permission-device-results.json and
ios-permission-device-provenance.json. Five permission validator regressions run in normal
and optimized Python, alongside the mandatory lifecycle evidence checks and optimized Swift
permission probe. Every release-level physical gate remains unchanged.
