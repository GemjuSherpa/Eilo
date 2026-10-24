import Foundation

/// Lab-only lifecycle observations. These are controller/SDK states, not acoustic measurements.
final class TrialLifecycle {
  static let cases = ["playback_stop", "playback_background", "playback_lock",
                      "capture_stop", "capture_background", "capture_lock"]
  private(set) var rows = [[String: Any]]()
  private(set) var current: String?
  private(set) var waitingForReturn = false
  private(set) var verifying = false
  private var began = false
  private var event: String?
  private var stopped = false
  private var attempt = 0
  var next: String? {
    for id in Self.cases {
      if !rows.contains(where: { $0["case"] as? String == id && $0["outcome"] as? String == "OBSERVED" }) {
        return rows.filter { $0["case"] as? String == id }.count < 3 ? id : nil
      }
    }
    return nil
  }
  var complete: Bool { Self.cases.allSatisfy { id in rows.contains { $0["case"] as? String == id && $0["outcome"] as? String == "OBSERVED" } } }
  func begin() -> String? {
    guard current == nil, let id = next else { return nil }
    current = id; attempt = rows.filter { $0["case"] as? String == id }.count + 1
    began = false; event = nil; stopped = false; waitingForReturn = false; verifying = false
    return id
  }
  @discardableResult func observedActive() -> Bool { guard current != nil,event == nil,!began else{return false};began=true;return true }
  func stoppedBy(_ cause: String, stopped: Bool) -> Bool {
    guard let id = current, event == nil else { return false }
    let expected = id.hasSuffix("_stop") ? "STOP_BUTTON" : "SCENE_RESIGNED"
    event = cause; self.stopped = stopped
    if cause != expected || !began || !stopped { finish("FAILED", resumed: false); return false }
    waitingForReturn = cause == "SCENE_RESIGNED"
    verifying = !waitingForReturn
    return verifying
  }
  func returned() -> Bool {
    guard current != nil, waitingForReturn else { return false }
    waitingForReturn = false; verifying = true; return true
  }
  func verified(stillStopped: Bool) {
    guard current != nil, verifying else { return }
    finish(stillStopped ? "OBSERVED" : "FAILED", resumed: !stillStopped)
  }
  func failed() { if current != nil { finish("FAILED", resumed: false) } }
  private func finish(_ outcome: String, resumed: Bool) {
    guard let id = current else { return }
    rows.append(["case": id, "attempt": attempt, "outcome": outcome,
                 "active_observed": began, "stop_event": event ?? "NONE",
                 "stopped_after_event": stopped, "resumption_observed": resumed,
                 "return_check_completed": verifying])
    current = nil; waitingForReturn = false; verifying = false
  }
  var aggregate: [String: Any] {
    ["schema_version": 1, "scope": "IOS_LAB_LIFECYCLE_OBSERVATIONS", "cases": rows,
     "phase": current != nil ? "IN_PROGRESS" : (complete ? "COMPLETED" : "PARTIAL"),
     "pending_case": current ?? "NONE", "physical_gate_acceptance": "NOT_RUN",
     "production": "NOT_ENABLED", "acoustic_stop_timing": "NOT_RUN",
     "locked_capture_support": "NOT_ENABLED", "network_observation": "NOT_RUN",
     "raw_audio_saved": false, "raw_text_exported": false,
     "lock_action": "OPERATOR_REQUESTED_NOT_OS_LOCK_PROOF"]
  }
}
