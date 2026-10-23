# Native confidence prototype review

The existing timestamp field is constant1.0 at the pinned Moonshine commit and cannot support the conversation confidence gate. This follow-up compiles a separate, minimal Android executable and extracts raw full-vocabulary softmax probabilities from the existing streaming model, using cached source/ORT/models and synthetic file input.

The six native cases pass greedy/draft token agreement and deliberate draft corruption rejection. Empty, malformed, NaN and out-of-range input is rejected with no score. Numeric edge cases, stale provenance, invalid scores, evidence promotion, case coverage and transcript injection have regression coverage in normal and optimized Python, including compiled C++ tests. Normal app checks are recorded with the final PR.

A failed early experiment assumed single-step/batched probabilities were equal within0.005. Actual differences reached0.146 despite token agreement; that assumption was removed. The final report retains both independently measured paths and their observed delta, without claiming equivalence. The cause remains unresolved. This prototype does not yet carry probabilities through the SDK's actual speculative divergence/cache-rewind branch, does not calibrate an utterance score, and does not authorize the production.85 threshold.

No large datasets, models, vendor source tree or compiled executable is committed. Complete applicable MIT notices accompany the source manifest. No app source, production policy, microphone permission or physical test status changes. See `packages/asr-confidence-probe/README.md` for scope and reproduction.
