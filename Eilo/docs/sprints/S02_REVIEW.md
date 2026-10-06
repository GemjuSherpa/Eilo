# S02 — Controller, cancellation and permission gates

Owner authorized S02 and scoped Git commands, with root sprint and per-task branches. Root sprint is sprint/s02-controller, based on verified S01 workflow branch. Each task merges into root sprint. No deployment or paid service is authorized. Existing root .DS_Store change is preserved.

Native Kotlin/Swift controller work is separate from real capture/ASR/model/TTS/storage integration in later sprints. Device permission/lifecycle tests remain provisional; no physical Android available and iPhone model/RAM unresolved.

- VC-LOCK-07 (task/s02-vc-lock-07): Bounded volatile typed diagnostics; Swift compiler/XCTest3 and Kotlin compiler/JUnit3 pass. No content, persistent log or upload sink.

- VC-CTRL-01 (task/s02-vc-ctrl-01): Native deterministic transition tables; 99 state/event pairs per platform plus synthetic turn/failure checks. Kotlin compile/JUnit5 and Swift compile/XCTest5 pass. Capturing maps to existing listening wire state.

- VC-CTRL-02 (task/s02-vc-ctrl-02): Serialized Stop cancels/releases/clears; cleanup failure still attempts every action and emits typed error. Synthetic committed history stays intact. Kotlin compile/JUnit7 and Swift compile/XCTest7 pass.

- VC-CTRL-03 (task/s02-vc-ctrl-03): Opaque native operation tokens invalidate old callbacks/audio across cancellation, Stop, new turns and controller instances. Reentrant Stop cannot restore speaking. Kotlin compile/JUnit10 and Swift compile/XCTest10 pass.

- VC-CTRL-04 (task/s02-vc-ctrl-04): Privacy epochs cancel work on lock/private/identity/reset transitions. Native guarded read/write/display effects deny stale callbacks and default memory access. Thread-delayed lock races, Kotlin compile/JUnit13 and Swift compile/XCTest13 pass.

- VC-CTRL-05 (task/s02-vc-ctrl-05): Native monotonic 60-second idle timer starts after playback, suspends while capturing/thinking/speaking and rejects stale timers. Context expiry preserves capture. Kotlin compile/JUnit15 and Swift compile/XCTest15 pass.

- VC-CTRL-06 (task/s02-vc-ctrl-06): End conversation invalidates pending output and clears active context while preserving enabled capture; cannot restart stopped/paused state. Kotlin compile/JUnit16 and Swift compile/XCTest16 pass.

- VC-CTRL-07 (task/s02-vc-ctrl-07): Native recognized stop listening routes directly to the same Stop transaction without a model call. Exact bounded command matching rejects stale recognition. Kotlin compile/JUnit18 and Swift compile/XCTest18 pass.

- VC-SET-04 (task/s02-vc-set-04): Android OS permission adapter and native capture gate require explicit Start plus current permission. Denial does not loop; delayed/duplicate grants, revocation and reentrant Stop fail closed. Kotlin compile/JUnit23 pass; physical prompt/permission tests not run.

- VC-SET-05 (task/s02-vc-set-05): iOS AVAudioApplication permission adapter (AVAudioSession fallback) compiles against installed iOS SDK. Native gate matches Android matrix and stale-grant/revocation tests. Swift compile/XCTest23 and Kotlin compile/JUnit23 pass; physical iOS prompts not run.

- VC-CTRL-08 (task/s02-vc-ctrl-08): Process-owned controller always starts stopped; no settings restoration invokes capture. Android activity binding and iOS protected-data/scene callbacks stop work. Opaque metadata snapshots and fresh-process tests pass (Kotlin JUnit25, Swift XCTest25); integrated unsigned iOS Release build passes.
