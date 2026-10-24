import Foundation

@main struct LifecycleProbe {
  static func main() {
    let state=TrialLifecycle()
    precondition(state.next == "playback_stop" && !state.complete)
    precondition(state.begin() == "playback_stop")
    precondition(state.begin() == nil)
    precondition(!state.stoppedBy("STOP_BUTTON",stopped:true))
    precondition(state.rows.count == 1 && state.rows[0]["outcome"] as? String == "FAILED")
    precondition(state.begin() == "playback_stop")
    precondition(state.observedActive())
    precondition(!state.observedActive())
    precondition(state.stoppedBy("STOP_BUTTON",stopped:true))
    state.verified(stillStopped:false)
    precondition(state.rows[1]["outcome"] as? String == "FAILED")
    precondition(state.begin() == "playback_stop")
    state.observedActive();precondition(state.stoppedBy("STOP_BUTTON",stopped:true))
    state.verified(stillStopped:true);state.verified(stillStopped:true)
    precondition(state.rows.count == 3 && state.next == "playback_background")
    for id in TrialLifecycle.cases.dropFirst() {
      precondition(state.begin() == id);state.observedActive()
      let event=id.hasSuffix("_stop") ? "STOP_BUTTON" : "SCENE_RESIGNED"
      let verify=state.stoppedBy(event,stopped:true)
      if event == "SCENE_RESIGNED" {
        precondition(!verify && state.waitingForReturn)
        state.verified(stillStopped:true)
        precondition(state.current == id)
        precondition(!state.stoppedBy("PROTECTED_DATA_UNAVAILABLE",stopped:true))
        precondition(state.returned() && !state.returned())
      } else { precondition(verify) }
      state.verified(stillStopped:true)
    }
    precondition(state.complete && state.begin() == nil)
    let failed=TrialLifecycle()
    for _ in 0..<3 {precondition(failed.begin() != nil);failed.observedActive();failed.failed()}
    precondition(failed.next == nil && !failed.complete)
    let wrong=TrialLifecycle();_ = wrong.begin();wrong.observedActive()
    precondition(!wrong.stoppedBy("SCENE_RESIGNED",stopped:true))
    precondition(wrong.rows[0]["outcome"] as? String == "FAILED")
    let release=TrialLifecycle();_ = release.begin();release.observedActive()
    precondition(!release.stoppedBy("STOP_BUTTON",stopped:false))
    precondition(release.rows[0]["outcome"] as? String == "FAILED")
    archiveChecks()
    print("Lifecycle state: ordering, early stop, wrong event, resumption, return requirement, duplicates, retry cap and release failure PASS. No OS operations.")
  }
  static func archiveChecks() {
    let manager=FileManager.default
    let root=manager.temporaryDirectory.appendingPathComponent("eilo-lifecycle-archive-test-"+UUID().uuidString)
    defer{try? manager.removeItem(at:root)}
    do {
      try manager.createDirectory(at:root,withIntermediateDirectories:true)
      var report=TrialLifecycle().aggregate
      report["process_session"]="00000000-0000-4000-8000-000000000001"
      report["os_build"]="Version 26.6.1 (Build 23G83)";report["physical_memory_bytes"]=8*1024*1024*1024
      report["updated_utc"]="2026-10-24T00:00:00Z"
      let source=root.appendingPathComponent("lifecycle-results.json")
      let original=try JSONSerialization.data(withJSONObject:report,options:.sortedKeys)
      try original.write(to:source)
      let current="00000000-0000-4000-8000-000000000002"
      let preserved0=try TrialLifecycleArchive.preserve(documents:root,currentSession:current);let check1 = preserved0;precondition(check1)
      let check2 = try Data(contentsOf:source)==original;precondition(check2)
      let folder=root.appendingPathComponent("lifecycle-archive")
      let archives=try manager.contentsOfDirectory(at:folder,includingPropertiesForKeys:nil)
      let archivedBytes=try Data(contentsOf:archives[0]);precondition(archives.count==1 && archivedBytes==original)
      let check4 = try TrialLifecycleArchive.preserve(documents:root,currentSession:current);precondition(check4)
      let check5 = try manager.contentsOfDirectory(at:folder,includingPropertiesForKeys:nil).count==1;precondition(check5)
      let check6 = !(try TrialLifecycleArchive.preserve(documents:root,currentSession:report["process_session"] as! String));precondition(check6)
      var changed=original;changed[0] ^= 1;try changed.write(to:archives[0])
      var collisionRejected=false
      do{_ = try TrialLifecycleArchive.preserve(documents:root,currentSession:current)}catch{collisionRejected=true}
      let kept=try Data(contentsOf:archives[0]);precondition(collisionRejected && kept==changed)
      try original.write(to:archives[0])
      report["phase"]="IN_PROGRESS";report["pending_case"]="playback_background"
      let pending=try JSONSerialization.data(withJSONObject:report,options:.sortedKeys);try pending.write(to:source)
      let check7 = try TrialLifecycleArchive.preserve(documents:root,currentSession:current);precondition(check7)
      let check8 = try Data(contentsOf:source)==pending;precondition(check8)
      report["transcript"]="synthetic forbidden field"
      let unexpected=try JSONSerialization.data(withJSONObject:report);try unexpected.write(to:source)
      var rejected=false
      do{_ = try TrialLifecycleArchive.preserve(documents:root,currentSession:current)}catch{rejected=true}
      let untouched=try Data(contentsOf:source);precondition(rejected && untouched==unexpected)
      report.removeValue(forKey:"transcript");try JSONSerialization.data(withJSONObject:report).write(to:source)
      try manager.removeItem(at:folder)
      let outside=root.appendingPathComponent("outside");try manager.createDirectory(at:outside,withIntermediateDirectories:false)
      try manager.createSymbolicLink(at:folder,withDestinationURL:outside)
      rejected=false;do{_ = try TrialLifecycleArchive.preserve(documents:root,currentSession:current)}catch{rejected=true}
      let outsideFiles=try manager.contentsOfDirectory(at:outside,includingPropertiesForKeys:nil);precondition(rejected && outsideFiles.isEmpty)
      print("Lifecycle archive: byte preservation, idempotence, same-session exclusion, interrupted-case retention, extra-content and symlink rejection PASS.")
    } catch {preconditionFailure("lifecycle archive fixture failed")}
  }

}
