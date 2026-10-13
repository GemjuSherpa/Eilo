# S06 / VC-VOICE-04 review

Android and Swift now provide a controller-owned native clause queue with one active clause, at most four waiting clauses, and 1024 UTF-8 bytes per clause or assembly buffer. Decoded fragments split at punctuation followed by whitespace or a newline; final sealing flushes the bounded remainder. A split decimal stays together. Overflow fails closed without truncating or indefinitely buffering text.

The current generation and output route are checked under the controller monitor before queue mutations and callbacks. Stop/privacy invalidation immediately drops queued references and schedules SDK cancellation without joining. Late and duplicate callbacks cannot drain another clause. The SDK start event moves the controller to speaking; a completed clause returns it to thinking while generation continues. Only a sealed, drained queue ends the turn. Model work remains valid during same-generation playback.

Authorization defaults to denied and is rechecked before every sink submission. S07 supplies the separate pre-speech safety policy and app integration; no ordinary app caller or readiness bypass is enabled. Reference release does not certify immutable String/SDK erasure, audio-stop timing or that a person heard the speech.

Validation: six focused Android and six focused Swift tests cover ordering, natural fragments, overflow, default denial, authorization revocation, SDK failure, Stop/late callbacks and concurrent generation/playback. Strict Swift compilation and Android lint pass. Normal app build and three fresh ten-second launches on the same iPhone 18 Pro simulator precede the commit. Final sprint evidence records the full native regression results. Physical acoustic/latency trials remain separate and unrun.

Final review safeguard: each active clause has a 60-second watchdog. A missing SDK completion fails closed, schedules stop, clears waiting text and rejects late callbacks; the timeout is not an acoustic-stop timing claim. A focused test on each platform verifies this stall case.
