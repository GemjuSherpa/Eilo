import Foundation
import AVFAudio

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
    print("{\"detections\":\(detections),\"closed_input_rejected\":true}")
  }
}
