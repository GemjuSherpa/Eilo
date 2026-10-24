import Foundation
import CryptoKit
import CoreFoundation

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

/// Preserve the prior process report byte-for-byte before a new process writes its own report.
/// Never infer completion of an interrupted case or resume audio from archived state.
enum TrialLifecycleArchive {
  enum Failure: Error { case unavailable }
  static func require(_ value: Bool) throws { if !value { throw Failure.unavailable } }
  static func preserve(documents: URL, currentSession: String) throws -> Bool {
    let manager=FileManager.default
    let source=documents.appendingPathComponent("lifecycle-results.json")
    guard manager.fileExists(atPath:source.path) else{return false}
    let values=try source.resourceValues(forKeys:[.isRegularFileKey,.isSymbolicLinkKey,.fileSizeKey])
    try require(values.isRegularFile == true && values.isSymbolicLink != true && (values.fileSize ?? 32769)<=32768)
    let data=try Data(contentsOf:source)
    try require(data.count<=32768)
    guard let r=try JSONSerialization.jsonObject(with:data) as? [String:Any] else{throw Failure.unavailable}
    let root:Set<String>=["schema_version","scope","cases","phase","pending_case","physical_gate_acceptance","production","acoustic_stop_timing","locked_capture_support","network_observation","raw_audio_saved","raw_text_exported","lock_action","process_session","os_build","physical_memory_bytes","updated_utc"]
    try require(Set(r.keys)==root && r["scope"] as? String == "IOS_LAB_LIFECYCLE_OBSERVATIONS")
    guard let version=r["schema_version"] as? NSNumber,CFGetTypeID(version) != CFBooleanGetTypeID(),version.intValue==1,
      let session=r["process_session"] as? String,UUID(uuidString:session) != nil,
      let os=r["os_build"] as? String,os.range(of:"^Version [0-9]+(\\.[0-9]+){1,3} \\(Build [A-Za-z0-9]+\\)$",options:.regularExpression) != nil,
      let memory=r["physical_memory_bytes"] as? NSNumber,CFGetTypeID(memory) != CFBooleanGetTypeID(),memory.int64Value>0,memory.int64Value<1<<40,
      let timestamp=r["updated_utc"] as? String,timestamp.count<=64,ISO8601DateFormatter().date(from:timestamp) != nil,
      let rows=r["cases"] as? [[String:Any]],rows.count<=18 else{throw Failure.unavailable}
    for (key,expected) in [("physical_gate_acceptance","NOT_RUN"),("production","NOT_ENABLED"),("acoustic_stop_timing","NOT_RUN"),("locked_capture_support","NOT_ENABLED"),("network_observation","NOT_RUN"),("lock_action","OPERATOR_REQUESTED_NOT_OS_LOCK_PROOF")] {
      try require(r[key] as? String == expected)
    }
    for key in ["raw_audio_saved","raw_text_exported"]{guard let value=r[key] as? NSNumber,CFGetTypeID(value)==CFBooleanGetTypeID(),!value.boolValue else{throw Failure.unavailable}}
    try require(["PARTIAL","IN_PROGRESS","COMPLETED"].contains(r["phase"] as? String ?? "") && (TrialLifecycle.cases+["NONE"]).contains(r["pending_case"] as? String ?? ""))
    for row in rows {
      try require(Set(row.keys)==Set(["case","attempt","outcome","active_observed","stop_event","stopped_after_event","resumption_observed","return_check_completed"]))
      try require(TrialLifecycle.cases.contains(row["case"] as? String ?? "") && ["OBSERVED","FAILED"].contains(row["outcome"] as? String ?? ""))
      guard let attempt=row["attempt"] as? NSNumber,CFGetTypeID(attempt) != CFBooleanGetTypeID(),(1...3).contains(attempt.intValue) else{throw Failure.unavailable}
      try require(["NONE","STOP_BUTTON","SCENE_RESIGNED","PROTECTED_DATA_UNAVAILABLE","AUDIO_INTERRUPTION_OR_ROUTE"].contains(row["stop_event"] as? String ?? ""))
      for key in ["active_observed","stopped_after_event","resumption_observed","return_check_completed"]{guard let value=row[key] as? NSNumber,CFGetTypeID(value)==CFBooleanGetTypeID() else{throw Failure.unavailable}}
    }
    if session == currentSession{return false}
    let folder=documents.appendingPathComponent("lifecycle-archive",isDirectory:true)
    if manager.fileExists(atPath:folder.path){let v=try folder.resourceValues(forKeys:[.isDirectoryKey,.isSymbolicLinkKey]);try require(v.isDirectory==true && v.isSymbolicLink != true)}
    else{try manager.createDirectory(at:folder,withIntermediateDirectories:false)}
    let digest=SHA256.hash(data:data).map{String(format:"%02x",$0)}.joined()
    let target=folder.appendingPathComponent(digest+".json")
    if manager.fileExists(atPath:target.path){let v=try target.resourceValues(forKeys:[.isRegularFileKey,.isSymbolicLinkKey,.fileSizeKey]);try require(v.isRegularFile==true && v.isSymbolicLink != true && v.fileSize==data.count);let archived=try Data(contentsOf:target);try require(archived==data)}
    else{try data.write(to:target,options:.atomic)}
    return true
  }
}
