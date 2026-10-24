import Foundation
import CoreFoundation

/// Real OS permission / native-controller boundary probe. This adapter cannot open hardware.
final class TrialPermissionCheck {
  final class ClosedEffects: ControllerEffects {
    private(set) var calls=0
    func startCapture()->Bool{calls+=1;return false}
    func playClause(_ clause:String)throws{throw Failure.closed}
    func cancelWork(){};func releaseCapture(){};func clearVolatileContext(){}
  }
  enum Failure:Error{case closed}
  let effects=ClosedEffects()
  let controller:NativeController
  private(set) var deniedInProcess=false
  init(permission:any MicrophonePermissionAdapter,models:any ModelReadinessAdapter){
    controller=NativeController(effects:effects,permission:permission,models:models)
  }
  func deny()->Bool {
    guard controller.modelStatus == .ready else{return false}
    // The OS adapter is checked by the caller and again by NativeController. The effects
    // adapter stays physically closed even if permission changes between those checks.
    return controller.dispatch(.start)
  }
  func refresh(){controller.permissionChanged()}
  func sample(kind:String,permission:String,accepted:Bool)->[String:Any]{
    let closed=effects.calls==0 && !controller.captureIsPending && [.stopped,.permissionRequired].contains(controller.state)
    let observed = kind=="DENIED_START" ? permission=="DENIED" && !accepted && closed && controller.state == .permissionRequired :
      kind=="RESTORED_NO_START" && permission=="GRANTED" && !accepted && closed
    let sameProcess=deniedInProcess
    if kind=="DENIED_START" && observed{deniedInProcess=true}
    return ["kind":kind,"permission":permission,"start_requested":kind=="DENIED_START","start_accepted":accepted,
            "capture_effect_calls":effects.calls,"capture_pending":controller.captureIsPending,
            "controller_state":controller.state.rawValue,"prior_denial_same_process":sameProcess,
            "outcome":observed ? "OBSERVED":"FAILED"]
  }
  /// Append-only bounded metadata ledger, including failures and separate process sessions.
  static func append(_ sample:[String:Any],to url:URL,session:String)throws {
    var rows=[[String:Any]]()
    if FileManager.default.fileExists(atPath:url.path){
      let values=try url.resourceValues(forKeys:[.isRegularFileKey,.isSymbolicLinkKey,.fileSizeKey])
      guard values.isRegularFile==true,values.isSymbolicLink != true,(values.fileSize ?? 32769)<=32768 else{throw Failure.closed}
      let data=try Data(contentsOf:url)
      guard let root=try JSONSerialization.jsonObject(with:data) as? [String:Any],
        Set(root.keys)==Set(["schema_version","scope","samples","raw_audio_saved","raw_text_exported","physical_gate_acceptance","hardware_capture","production"]),
        root["schema_version"] as? Int==1,root["scope"] as? String=="IOS_OS_PERMISSION_BOUNDARY",
        root["raw_audio_saved"] as? Bool==false,root["raw_text_exported"] as? Bool==false,
        root["physical_gate_acceptance"] as? String=="NOT_RUN",root["hardware_capture"] as? String=="NOT_OPENED",
        root["production"] as? String=="NOT_ENABLED",let previous=root["samples"] as? [[String:Any]] else{throw Failure.closed}
      rows=previous
    }
    if sample["kind"] as? String=="RESTORED_NO_START" {
      guard rows.contains(where:{$0["kind"] as? String=="DENIED_START" && $0["outcome"] as? String=="OBSERVED"}) else{throw Failure.closed}
    }
    var row=sample;row["process_session"]=session;row["updated_utc"]=ISO8601DateFormatter().string(from:Date())
    rows.append(row)
    guard rows.count<=8 else{throw Failure.closed}
    let keys=Set(["kind","permission","start_requested","start_accepted","capture_effect_calls","capture_pending","controller_state","prior_denial_same_process","outcome","process_session","updated_utc"])
    for value in rows {
      guard Set(value.keys)==keys,["DENIED_START","RESTORED_NO_START"].contains(value["kind"] as? String ?? ""),
        ["DENIED","GRANTED","UNAVAILABLE"].contains(value["permission"] as? String ?? ""),
        ["OBSERVED","FAILED"].contains(value["outcome"] as? String ?? ""),
        ControllerState.allCases.map(\.rawValue).contains(value["controller_state"] as? String ?? ""),
        UUID(uuidString:value["process_session"] as? String ?? "") != nil,
        let date=value["updated_utc"] as? String,ISO8601DateFormatter().date(from:date) != nil,
        let calls=value["capture_effect_calls"] as? Int,(0...16).contains(calls) else{throw Failure.closed}
      let denied=value["kind"] as? String=="DENIED_START"
      guard value["start_requested"] as? Bool==denied else{throw Failure.closed}
      if value["outcome"] as? String=="OBSERVED" {
        guard value["permission"] as? String==(denied ? "DENIED":"GRANTED"),
          value["start_accepted"] as? Bool==false,calls==0,value["capture_pending"] as? Bool==false,
          (denied ? value["controller_state"] as? String=="permission_required" :
           ["stopped","permission_required"].contains(value["controller_state"] as? String ?? "")) else{throw Failure.closed}
      }
      for key in ["start_requested","start_accepted","capture_pending","prior_denial_same_process"] {
        guard let boolean=value[key] as? NSNumber,CFGetTypeID(boolean)==CFBooleanGetTypeID() else{throw Failure.closed}
      }
    }
    let report:[String:Any]=["schema_version":1,"scope":"IOS_OS_PERMISSION_BOUNDARY","samples":rows,
      "raw_audio_saved":false,"raw_text_exported":false,"physical_gate_acceptance":"NOT_RUN",
      "hardware_capture":"NOT_OPENED","production":"NOT_ENABLED"]
    try JSONSerialization.data(withJSONObject:report,options:.sortedKeys).write(to:url,options:.atomic)
  }
}
