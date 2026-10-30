# S07 joined framework execution

This increment closes the gap between the isolated packaged ASR test and the
existing loose-library joined simulator evaluation. The relocated client loads
CEiloAsr from its embedded Frameworks directory, alongside static ONNX VAD and
freshly rebuilt llama CPU libraries. It installs verified model files through a
signed lab pack and executes speech, follow-up and silence cases.

The evaluator-only clause sink uses real SDK callbacks at gain zero. Speech and
follow-up must each start exactly one LLM reply and complete SDK speech; silence
must not start inference. Context remains volatile. Aggregate source/model/binary
hashes, counters and transcript digests are retained; no transcript, reply or audio
is committed. The runner verifies reviewed framework identity, relative loader
paths, the original client directory's absence, all compiled sources/headers and
model hashes before and after execution.

Physical gates remain OPEN / NOT_RUN, ordinary-app activation NOT_ENABLED,
persistent memory DISABLED and S08/release HOLD. Confidence remains synthetic,
calibration NOT_ESTABLISHED, threshold NOT_GRANTED, lab trust synthetic, signing
NOT_REVIEWED and distribution NOT_APPROVED. Muted simulator SDK completion does
not establish real offline voice availability or device acoustics.

Validation: actual native execution; adversarial report mutation checks in normal
and optimized Python; existing joined evidence and repository gated workflows.
