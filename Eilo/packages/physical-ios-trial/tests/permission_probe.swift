import Foundation

final class Permission:MicrophonePermissionAdapter {
  var value:MicrophonePermission = .denied
  func status()->MicrophonePermission{value}
  func request(_ completion:@escaping(MicrophonePermission)->Void){preconditionFailure("No permission prompt expected")}
}
struct Ready:ModelReadinessAdapter{func status()->ModelStatus{.ready}}
@main struct PermissionProbe {
  static func main()throws {
    let permission=Permission(),check=TrialPermissionCheck(permission:Permission(),models:Ready())
    precondition(!check.deny())
    let denied=check.sample(kind:"DENIED_START",permission:"DENIED",accepted:false)
    precondition(denied["outcome"] as? String=="OBSERVED" && check.effects.calls==0)
    let retained=TrialPermissionCheck(permission:permission,models:Ready());precondition(!retained.deny())
    _ = retained.sample(kind:"DENIED_START",permission:"DENIED",accepted:false)
    permission.value = .granted;retained.refresh()
    let restored=retained.sample(kind:"RESTORED_NO_START",permission:"GRANTED",accepted:false)
    precondition(restored["outcome"] as? String=="OBSERVED" && restored["prior_denial_same_process"] as? Bool==true && retained.effects.calls==0)
    // If a Start is mistakenly called after restoration, the closed adapter rejects it,
    // and the observation fails rather than claiming a zero-capture permission pass.
    _ = retained.deny()
    precondition(retained.sample(kind:"RESTORED_NO_START",permission:"GRANTED",accepted:false)["outcome"] as? String=="FAILED")
    let file=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString+".json")
    defer{try? FileManager.default.removeItem(at:file)}
    let session=UUID().uuidString
    // A granted-first check is a missing prerequisite, not proof of a storage failure.
    var prerequisiteRejected=false
    do{try TrialPermissionCheck.append(restored,to:file,session:session)}catch{prerequisiteRejected=true}
    precondition(prerequisiteRejected && !FileManager.default.fileExists(atPath:file.path))
    try TrialPermissionCheck.append(denied,to:file,session:session)
    try TrialPermissionCheck.append(restored,to:file,session:session)
    let saved=try Data(contentsOf:file)
    let r=try JSONSerialization.jsonObject(with:saved) as! [String:Any]
    precondition((r["samples"] as! [[String:Any]]).count==2)
    var bad=denied;bad["transcript"]="synthetic forbidden field"
    var rejected=false;do{try TrialPermissionCheck.append(bad,to:file,session:session)}catch{rejected=true}
    precondition(rejected);let unchanged=try Data(contentsOf:file);precondition(unchanged==saved)
    for _ in 0..<6{try TrialPermissionCheck.append(denied,to:file,session:session)}
    rejected=false;do{try TrialPermissionCheck.append(denied,to:file,session:session)}catch{rejected=true};precondition(rejected)
    print("OS permission boundary probe: denied Start blocks effects, restore never starts, accidental Start fails, cross-session append preserves rows, extra content and bounds rejected PASS. Synthetic permission; no OS or hardware operation.")
  }
}
