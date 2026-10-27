# S05 dependency — development-only calibrator, new-utterance pilot

The previous 30 development observations fit separate monotonic mappings for greedy and
self-draft scores. The private fitted values and public hash were frozen before new test inference.
An initial unseen-speaker selection failed on metadata capacity: all curator dev/test speakers
had already appeared in earlier experiments. Before inference the protocol was explicitly amended
and committed as `5f43981ea9ef849940aac85b508d1ccc73e4066c`, with unchanged fitted values.
The actual cohort has 30 new utterances from 30 known curator-test speakers. Fitting development
speakers and all 90 prior utterance/encoded/PCM values are excluded. No source train row was used
or relabeled. This is not an independent unseen-speaker trial and does not establish model-training
exclusion. The narrower scope and initial failure are retained rather than silently substituted.

Actual isolated API35 ARM64 emulator execution using the existing verified native collector found
29 available scores and 23 exact transcriptions in each path. At the unchanged descriptive 0.85
cutoff raw scores accept 29 with six errors; mapped scores accept 20 with zero observed errors.
Coverage retains all 30 cases. Brier falls from 0.166346 to 0.087404 greedy and 0.166375 to 0.107983
self-draft, over available scores. Four/three scores respectively use endpoint clamping outside
the development score range. Small empirical blocks, known test speakers, exact-match proxy
labels and only 20 accepted cases prevent production qualification or a zero-risk claim.

`packages/asr-calibration` contains the development fitter, scope protocol, public freeze hash,
bounded selector/independent verifier, committed-blob guarded evaluator, observed aggregate report
and strict JSON/HTML exporter. Private knots and case scores stay in ignored local storage.
No native collector/model/runtime or ordinary app policy was changed; no threshold fitting or test
refitting occurred. The new prototype build is within the existing 5 GiB cap; source/model/cache
hashes, invalid input rejection and scratch cleanup use the prior reviewed runner. No new download,
package, terms, hardware audio, account, signing or physical-device access occurred.

Thirteen tests pass in normal/optimized Python; CI also checks current pins and aggregate arithmetic
without datasets/models. Hosted normal native checks still gate the PR. The emulator started for
this file-fed run was stopped, prior evidence and personal edits preserved. All 120 clean clips
examined so far are now consumed; future test freshness must exclude this new cohort too.

This improves pilot discrimination at one descriptive cutoff; it does not close VC-TURN-06,
calibration qualification, noise/streaming validation or separately authorized caller/runtime
integration. Production confidence stays disabled, threshold authorization NOT_GRANTED,
model-training overlap UNKNOWN, S08/release HOLD, persistent memory disabled and physical gates OPEN.
