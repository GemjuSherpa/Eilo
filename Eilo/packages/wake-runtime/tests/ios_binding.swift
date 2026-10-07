import Foundation
import AVFAudio

// Standalone synthetic control only. Never included in the application target or real permission flow.
private struct EvaluationPermission:MicrophonePermissionAdapter {
  func status()->MicrophonePermission { .granted }
  func request(_ completion:@escaping (MicrophonePermission)->Void) { completion(.granted) }
}
private struct EvaluationModels:ModelReadinessAdapter { func status()->ModelStatus { .ready } }
private final class EvaluationCapture:ControllerEffects {
  func startCapture()->Bool { true } // No audio device; frames come only from verified synthetic files.
  func playClause(_ clause:String) throws { throw WakeFailure.unavailable }
  func cancelWork() {}
  func releaseCapture() {}
  func clearVolatileContext() {}
}

/// Standalone simulator evaluation, synthetic verified fixtures only. Never linked into Eilo UI.
@main struct IOSWakeBindingEvaluation {
  static func main() throws {
    guard CommandLine.arguments.count==3 else { throw WakeFailure.unavailable }
    let directory=CommandLine.arguments[1]
    let paths=try WakeModelPaths(
      encoder:directory+"/encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx",
      decoder:directory+"/decoder-epoch-12-avg-2-chunk-16-left-64.onnx",
      joiner:directory+"/joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx",tokens:directory+"/tokens.txt")
    let configuration=try WakeConfiguration(phrase:"HEY EILO",threshold:0.125,boost:1.5)
    // The invoking verifier checks all model and fixture hashes before this process runs.
    let stream=try NativeWakeStream(paths:paths,configuration:configuration,verified:{true})
    defer { stream.close() }
    let file=try AVAudioFile(forReading:URL(fileURLWithPath:CommandLine.arguments[2]))
    guard file.processingFormat.channelCount==1,file.processingFormat.sampleRate==16000,
      file.length>0,file.length<=16000*30,
      let buffer=AVAudioPCMBuffer(pcmFormat:file.processingFormat,frameCapacity:AVAudioFrameCount(file.length)) else {
      throw WakeFailure.unavailable
    }
    try file.read(into:buffer)
    guard let input=buffer.floatChannelData?[0] else { throw WakeFailure.unavailable }
    defer { input.update(repeating:0,count:Int(buffer.frameLength)) }
    var detections=0
    func accept(_ samples:UnsafeBufferPointer<Float>) throws {
      try stream.accept(samples,sampleRate:16000)
      guard try !stream.ready() else { throw WakeFailure.unavailable }
      if try stream.keyword()=="HEY EILO" { detections += 1;try stream.reset() }
    }
    for offset in stride(from:0,to:Int(buffer.frameLength),by:320) {
      try accept(UnsafeBufferPointer(start:input+offset,count:min(320,Int(buffer.frameLength)-offset)))
    }
    try [Float](repeating:0,count:320).withUnsafeBufferPointer { tail in
      for _ in 0..<50 { try accept(tail) }
    }
    stream.close();stream.close()
    // Explicit release must permanently reject later input.
    var rejected=false
    do { try [Float(0)].withUnsafeBufferPointer { try stream.accept($0,sampleRate:16000) } }
    catch { rejected=true }
    guard rejected else { throw WakeFailure.unavailable }
    let controller=NativeController(effects:EvaluationCapture(),permission:EvaluationPermission(),models:EvaluationModels())
    guard controller.dispatch(.start),let token=controller.token else { throw WakeFailure.unavailable }
    let detector=WakeDetector(configuration:configuration,verified:{true},open:{config in
      try NativeWakeStream(paths:paths,configuration:config,verified:{true})
    })
    // Deterministic receive clock: validate transport, not real-time device performance.
    var time:UInt64=0
    let delivery=try WakeFrameDelivery(sampleRate:16000,detector:detector,token:token,now:{time})
    defer { delivery.close() }
    var delivered=[WakeCaptureActivation](),pending=0
    func drain() throws {
      guard case .events(let events)=delivery.drain() else { throw WakeFailure.unavailable }
      delivered.append(contentsOf:events);pending=0
    }
    func enqueue(_ samples:UnsafeBufferPointer<Float>) throws {
      guard delivery.submit(samples,sampleRate:16000) else { throw WakeFailure.unavailable }
      time+=20_000_000;pending+=1;if pending==3 {try drain()}
    }
    for offset in stride(from:0,to:Int(buffer.frameLength),by:320) {
      try enqueue(UnsafeBufferPointer(start:input+offset,count:min(320,Int(buffer.frameLength)-offset)))
    }
    try [Float](repeating:0,count:320).withUnsafeBufferPointer {tail in for _ in 0..<50 {try enqueue(tail)} }
    try drain()
    guard delivered.count==detections else { throw WakeFailure.unavailable }
    if let event=delivered.first {
      guard event.apply(controller),controller.state == .capturing else { throw WakeFailure.unavailable }
    } else { guard controller.state == .standby else { throw WakeFailure.unavailable } }
    controller.stop();delivery.close()
    let staleRejected=delivered.allSatisfy {!$0.apply(controller)}
    let closedDeliveryRejected=[Float(0)].withUnsafeBufferPointer {!delivery.submit($0,sampleRate:16000)}
    guard staleRejected,closedDeliveryRejected else { throw WakeFailure.unavailable }
    print("{\"detections\":\(detections),\"closed_input_rejected\":true,\"delivery_detections\":\(delivered.count),\"delivery_closed_rejected\":true}")
  }
}
