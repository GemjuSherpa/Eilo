# VC-TURN-04 — duration-aware native endpoint receiver

PR63 is reviewed/merged at main 36efdf9; all eight CI checks pass. This checkpoint continues
VC-TURN-04 on task/vc-turn-04-native-endpoint-clock -> sprint/native-vad-endpoint, with a PR for
review before main. It preserves the normal unavailable model/capture readiness defaults.

Both native policies now consume genuine 512-sample/32 ms model observations through a separate
path, retaining the legacy strict 320-sample/20 ms API. Clocks cannot be mixed. Absolute sample
positions must be contiguous; duplicate/gapped input, invalid scores/counts and nonfinal partial
windows revoke the detector permanently. No probability is repeated/interpolated into fake frames.

The original sample thresholds remain: 2,560 high samples confirm speech, at least 8,000 low
samples complete it, 80,000 samples without speech time out, and 480,000 bound the turn. Full
native silence windows reach completion at 8,192 samples (512 ms), never before 500 ms; timestamps
are not backdated. The next-input budget forces genuine short final windows at the five-second
and thirty-second bounds, excluding all padding. Premature EOF is INCOMPLETE, not a manufactured
speech/no-speech result. Unknown probabilities continue to reset high/silence accumulation.

The worker-confined NativeVadEndpointBridge defaults to a denied lease. It checks native model/
controller validity before providing capacity and before/after consuming each observation. Lost
lease/close cannot revive; an otherwise completed decision is withheld when the final lease check
fails. The receiver owns no native handles. Its future native caller must independently guard
inference, destroy the stream on terminal results and revalidate the controller token on commit.
No JS bridge, model trust, ASR confidence, independent speech/echo route, interruption or locked
policy is enabled by this receiver.

Validation:

- 228 Swift XCTest cases PASS (ten new endpoint tests); 278 Android JUnit cases PASS (ten new),
  zero failures/errors/skips. Android compilation and lint pass with existing unrelated warnings.
- New cases cover native confirmation/silence, exact input budgets, early EOF, padding exclusion,
  invalid probabilities, gaps/duplicates/mixed clocks, uncertain evidence and lease revocation
  before input and after an otherwise completed endpoint. Legacy endpoint cases still pass.
- Actual approved Silero -> C ABI -> Swift receiver runs on the same iPhone18 Pro/iOS27 simulator:
  157 native windows consume exactly 80,000 samples and return NO_SPEECH on synthetic silence.
  Source/model hashes are in packages/vad-runtime/tests/endpoint-results.json. Lease revocation
  is separately scripted, not claimed as acoustic/controller evidence. No Android JNI execution.
- Normal final iPhone18 Pro simulator Debug build/install and three fresh ten-second startup
  checks pass before commit. App startup is not voice recognition or physical audio evidence.
- Native sanitizer contracts and Python compilation pass. No new dependencies/downloads; existing
  node_modules/Pods were temporarily reused. Original three personal edits retain their exact
  diff hash and are excluded. Hosted CI is recorded separately on the review PR.

Next: native Swift/Kotlin handle lifetime bindings, lease-guarded buffering/delivery and capture
attachment. This task does not close VC-TURN-04 physical acceptance. Public VAD accuracy still
needs exported human time-aligned labels. All physical gates NOT_RUN, production NOT_ENABLED and
S08 feasibility remains on hold. No automatic main merge, history rewrite or new stable task IDs.
