# Native signed speech evaluation

PR73's S10 readiness work was merged at `74aec514b7cabbea17f44d0710a602395532dee7`.
This continuation evaluates an earlier voice prerequisite with real cached models. It does not
implement S10 storage or accept VC-GATE-04. S08 remains HOLD; persistent memory remains denied.

## Delivered scope

Separate task branches `task/signed-speech-ios-evaluation`, `task/signed-speech-jni-evaluation`
and `task/signed-speech-evidence-ci` consolidate into `sprint/native-signed-speech-evaluation`.
One final PR is presented for review. No main merge is authorized by this continuation.

Both offline runners verify approved cached runtime/model archives and extracted files,
then use ephemeral ES256 lab signatures with the production nine-artifact installer and leases.
The simulator and macOS host JNI both passed:

| Case | Observed result on both |
|---|---|
| Synthetic 16 kHz speech | One recognized result; 29184 normalized samples |
| Synthetic 48 kHz speech | One recognized result; same normalized count and transcript hash |
| 80000 quiet normalized samples | No speech; zero ASR opens |
| Stop during real ASR finalization | Zero recognized/metadata callbacks |
| Pack replacement during real ASR finalization | Zero recognized/metadata callbacks |
| Idle Stop with no subsequent frame | VAD closes; zero ASR opens/results |
| Stale setup ticket | Installer rejects; no native opens |
| Corrupt signed artifact | Installer rejects; no native opens |

Each platform opened/closed six VAD handles and four ASR handles, and made 386 VAD calls.
Every native create/process/accept/text/destroy operation ran on a separate worker. Each
positive speech case made 19 ASR accept calls. No raw transcript/audio, model weights, libraries,
account credentials or local absolute cache paths are committed. Temporary lab stores are removed.

The ASR wrapper exports exactly four Eilo C symbols with two-level namespace isolation so its
bundled ONNX runtime can coexist with VAD's runtime. Host JNI uses the unchanged three-library
ASR loader and two-library VAD loader. Production sources and activation remain unchanged.

## Validation

The committed per-platform results and exact source/report pins are under
`packages/vad-runtime/tests/signed-installer-*.json`. Synthetic CI validates exact report fields,
source hashes, model inventory, all eight cases, cross-platform equality and tampering failures,
in normal and optimized Python. It uses no downloads, models, audio device or native SDK.
Actual native execution remains opt-in local evidence, not a hosted CI inference claim.

All 305 Swift tests and all 361 normal Android tests passed with zero failures/errors/skips.
Android lint, release Kotlin compilation, debug and release assembly passed offline. Before
each code task commit, the normal iPhone 18 Pro simulator app is built, installed, and launched
fresh three times with ten-second dwell. Workspace checks and secret scans precede publication.
The original personal Xcode/plist/S02 edits remain byte-identical.

## Remaining gates

This is one synthetic utterance plus silence and lifecycle negative cases. It establishes
real signed installer wiring, not acoustic accuracy, 48 kHz hardware route quality, Android ART,
physical microphone/speaker behavior, latency, interruption/separation, battery, screen-off or
OS authentication results. Physical gates remain NOT_RUN and production remains NOT_ENABLED.
The ephemeral lab key and evidence strings do not approve production trust or model licensing.

The next queue item is the selected physical-device prerequisite matrix and foreground joined
voice trial, followed by measured latency/interruption/energy evidence and a reviewed VC-GATE-04
feasible-scope decision. Physical access and any consequential activation must be authorized
for the selected configuration before conducting those trials. S10 remains dependency-blocked.
