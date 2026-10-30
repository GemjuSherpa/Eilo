import Foundation
#if DEBUG || EILO_ASR_EVALUATION || EILO_VAD_EVALUATION || EILO_LLM_EVALUATION
#error("App framework gate probe requires Release runtime guards")
#endif
#if !canImport(CEiloAsr)
#error("Gate probe must import the packaged ASR framework")
#endif
@main struct FrameworkReleaseGateProbe {
  final class Effects:ControllerEffects {
    var starts=0
    func startCapture()->Bool{starts+=1;return true}
    func playClause(_ clause:String)throws{}
    func cancelWork(){};func releaseCapture(){};func clearVolatileContext(){}
  }
  struct Permission:MicrophonePermissionAdapter {
    func status()->MicrophonePermission{.granted}
    func request(_ complete:@escaping(MicrophonePermission)->Void){complete(.granted)}
  }
  static func main(){
    let effects=Effects(),controller=NativeController(effects:effects,permission:Permission())
    guard NativeAsrAPI.linked.create("/unavailable-evaluator-model") == nil,
          controller.modelStatus == .missing,!controller.dispatch(.start),effects.starts==0,controller.token == nil else{exit(1)}
    controller.stop()
    print("FRAMEWORK_RELEASE_GATES_PASS")
  }
}
