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
    print("Lifecycle state: ordering, early stop, wrong event, resumption, return requirement, duplicates, retry cap and release failure PASS. No OS operations.")
  }
}
