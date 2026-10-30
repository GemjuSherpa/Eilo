# S07 opt-in simulator app framework embedding

The standalone and joined evaluator clients established ASR framework behavior.
This increment tests Xcode-managed linking/embedding in the normal Eilo Release
simulator app, with its production model and ASR guards preserved.

A temporary project copy adds one framework link and one Copy Files phase, sets
its local deployment target to 18.0, disables signing and copy-phase stripping,
and adds no runtime evaluation flag. The original project is unchanged. Existing
Pods, archives, facades and Node dependencies are reused without installation or
downloads. A regular private Pods copy preserves project-relative paths; the
personal checkout is never changed.

The artifact inspector requires the exact reviewed framework binary and metadata,
a required dynamic load, relative Frameworks loader path, ARM64 simulator Release
identity, no developer signature/provision, and no named model/audio resources.
A separate optimized Swift probe imports that framework with all runtime evaluation
flags absent; it confirms unavailable ASR, default missing-model readiness and no
capture start despite synthetic permission. Three ten-second fresh simulator
process launches check loading stability; they do not prove UI, audio or physical
behavior. The normal app does not receive models, trust keys or readiness overrides.

Initial argument/path failures and Xcode's automatic framework stripping were
retained locally. Copy-phase stripping is disabled rather than relaxing exact-byte
identity. Source and cached archive hashes are checked before/after the final run.
Native binaries, raw logs and dependency archives remain ignored; CI audits only
committed aggregate evidence and adversarial scope/graph regressions.

Ordinary voice remains NOT_ENABLED, physical gates OPEN/NOT_RUN, S08/release HOLD,
persistent memory DISABLED, signing NOT_REVIEWED and distribution NOT_APPROVED.
License/trust/caller, calibrated confidence, voice evidence and actual device
acceptance remain prerequisites for activation.
