# S05 VC-TURN-06 dependency: SDK score propagation

An isolated v0.1.5 source overlay now carries selected-token raw pre-bias probabilities through
actual decode_full greedy/speculative verification and divergence cache-reset paths. It does
not upgrade the ordinary app runtime or open the confidence policy gate.

Six synthetic ARM64/API35 emulator fixtures produced 29 complete diagnostic paths and one
explicit unavailable biased decode. Fifty-four injected/invalid/empty/capped cases produced no
usable partial scores. Exact captured-row long-double comparison was within 2.94301236e-14;
original and instrumented SDK token outputs matched for complete paths. Controlled repeated
shapes were stable, while batch/step probabilities still differed by up to 0.145611985 and
full/prefix by 0.114998032. The cause remains unestablished; score sources cannot be pooled.

Implementation, failed experiments, final aggregate report, pins, license notices and offline
reproduction are in packages/asr-sdk-score-probe. Upstream cache integrity was checked; no
new source/model/package download, physical audio, phone test or shipping-runtime change occurred.
CI checks actual evidence and nine regressions, including native ASan/UBSan boundary cases.

This closes the invocation-level propagation experiment, not VC-TURN-06 production acceptance.
Calibration on a held-out labelled corpus and reviewed app/runtime integration remain needed.
Physical gates remain open under the user's explicit instruction; release remains HOLD and
memory remains disabled. No extra sprint or physical pass is inferred.
