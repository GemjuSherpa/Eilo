# S02 — Controller, cancellation and permission gates

Owner authorized S02 and scoped Git commands, with root sprint and per-task branches. Root sprint is sprint/s02-controller, based on verified S01 workflow branch. Each task merges into root sprint. No deployment or paid service is authorized. Existing root .DS_Store change is preserved.

Native Kotlin/Swift controller work is separate from real capture/ASR/model/TTS/storage integration in later sprints. Device permission/lifecycle tests remain provisional; no physical Android available and iPhone model/RAM unresolved.

- VC-LOCK-07 (task/s02-vc-lock-07): Bounded volatile typed diagnostics; Swift compiler/XCTest3 and Kotlin compiler/JUnit3 pass. No content, persistent log or upload sink.

- VC-CTRL-01 (task/s02-vc-ctrl-01): Native deterministic transition tables; 99 state/event pairs per platform plus synthetic turn/failure checks. Kotlin compile/JUnit5 and Swift compile/XCTest5 pass. Capturing maps to existing listening wire state.

- VC-CTRL-02 (task/s02-vc-ctrl-02): Serialized Stop cancels/releases/clears; cleanup failure still attempts every action and emits typed error. Synthetic committed history stays intact. Kotlin compile/JUnit7 and Swift compile/XCTest7 pass.

- VC-CTRL-03 (task/s02-vc-ctrl-03): Opaque native operation tokens invalidate old callbacks/audio across cancellation, Stop, new turns and controller instances. Reentrant Stop cannot restore speaking. Kotlin compile/JUnit10 and Swift compile/XCTest10 pass.
