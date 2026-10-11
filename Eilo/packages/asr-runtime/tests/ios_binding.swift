import Foundation
private struct SyntheticPermission:MicrophonePermissionAdapter {
  func status()->MicrophonePermission{.granted}
  func request(_ completion:@escaping(MicrophonePermission)->Void){completion(.granted)}
}
private struct SyntheticModels:ModelReadinessAdapter{func status()->ModelStatus{.ready}}
private final class SyntheticEffects:ControllerEffects {
  func startCapture()->Bool{true}
  func playClause(_ clause:String) throws{}
  func cancelWork() throws{}
  func releaseCapture() throws{}
  func clearVolatileContext() throws{}
}
/// Explicit synthetic file runner compiled outside the normal app target; never opens a mic.
@main struct AsrBindingEvaluation {
  static func main() throws {
    guard CommandLine.arguments.count==3 else{throw AsrFailure.unavailable}
    let model=CommandLine.arguments[1],data=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2]))
    guard !data.isEmpty,data.count%4==0,data.count<=480000*4 else{throw AsrFailure.unavailable}
    var pcm=data.withUnsafeBytes{Array($0.bindMemory(to:Float.self))}
    let controller=NativeController(effects:SyntheticEffects(),permission:SyntheticPermission(),models:SyntheticModels())
    guard controller.dispatch(.start),controller.dispatch(.speechDetected,token:controller.token),let token=controller.token else{throw AsrFailure.unavailable}
    let stream=StreamingAsr(token,allowed:{!token.cancelled},open:{try NativeAsrStream(directory:model,verified:{true})})
    var frames=0
    for i in stride(from:0,to:pcm.count,by:320){
      let end=min(i+320,pcm.count)
      guard pcm.withUnsafeBufferPointer({stream.accept(UnsafeBufferPointer(rebasing:$0[i..<end]))}) else{throw AsrFailure.unavailable}
      frames+=1
      if frames%10==0 && stream.poll()==nil{throw AsrFailure.unavailable}
    }
    pcm.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}
    guard let final=stream.poll(finish:true),final.final,stream.poll(finish:true)==nil else{throw AsrFailure.unavailable}
    let cancelled=StreamingAsr(token,allowed:{!token.cancelled},open:{try NativeAsrStream(directory:model,verified:{true})})
    guard [Float](repeating:0,count:320).withUnsafeBufferPointer({cancelled.accept($0)}) else{throw AsrFailure.unavailable}
    controller.stop();guard cancelled.poll(finish:true)==nil else{throw AsrFailure.unavailable}
    // Text here is from the independently checksum-frozen synthetic fixture only.
    print(final.text)
  }
}
