# S06 / VC-VOICE-05 review

The native clause queue now exposes a default-denied, metadata-only progress snapshot: produced, queued, SDK started, SDK finished, interruption requested, SDK interrupted, failure and discarded before start. There is no text/audio/wall clock, heard flag, JS bridge or persistence. The volatile ledger retains at most 32 clause records.

Stop mid-clause records an interruption request and drops waiting clauses. A late finish callback cannot convert that request into completed playback. An SDK interruption callback received while the generation is current is recorded separately from the request. SDK start/finish are not proof of first audible sound or that Gemju Sherpa heard the speech.

Access is serialized with privacy transitions, denied by default and clears/rejects the ledger when its privacy epoch is stale or the app is locked. An active queue clears immediately on privacy cancellation. A completed/cancelled queue's remaining metadata is discarded on its next attempted access after a privacy change. S08 will supply protected history authorization/storage; no history writes are enabled here.

Validation: nine queue/progress tests per platform include mid-clause Stop, stale completion, default-denied metadata access, privacy invalidation, finished-versus-interrupted status and the 32-record bound. Android lint and strict Swift compilation pass. Normal app build and three fresh ten-second launches on the same iPhone 18 Pro simulator precede commit. Physical acoustic playback/stop timing remains unrun.
