import Foundation

struct AsrText { let text:String; let final:Bool }
protocol AsrStream:AnyObject {
  /// Synchronous borrowed PCM on the native worker; no retained buffer or content logging.
  func accept(_ pcm:UnsafeBufferPointer<Float>) throws
  func text(finish:Bool) throws -> String
  func close()
}
/// Confined to one native worker. Cancellation is immediate on the token; backend cleanup runs
/// on this worker, outside controller/capture locks. No default runtime/model activation.
final class StreamingAsr {
  private let token:GenerationToken,allowed:()->Bool,open:() throws -> AsrStream
  private var stream:AsrStream?,samples=0,closed=false
  private var scratch=[Float](repeating:0,count:1600)
  init(_ token:GenerationToken,allowed:@escaping ()->Bool,open:@escaping () throws -> AsrStream){self.token=token;self.allowed=allowed;self.open=open}
  private var valid:Bool{!closed && !token.cancelled && allowed()}
  func accept(_ pcm:UnsafeBufferPointer<Float>)->Bool {
    guard (1...1600).contains(pcm.count),samples<=480000-pcm.count,valid,pcm.allSatisfy({$0.isFinite && (-1...1).contains($0)}) else{close();return false}
    defer{scratch.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
    do {
      if stream == nil{stream=try open()}
      guard valid else{close();return false}
      for i in pcm.indices{scratch[i]=pcm[i]}
      try scratch.withUnsafeBufferPointer{try stream!.accept(UnsafeBufferPointer(rebasing:$0[0..<pcm.count]))}
      samples+=pcm.count
      guard valid else{close();return false};return true
    } catch{close();return false}
  }
  func poll(finish:Bool=false)->AsrText? {
    guard valid,let current=stream else{close();return nil}
    do {
      let text=try current.text(finish:finish)
      guard valid,text.utf8.count<=4096,!text.unicodeScalars.contains(where:{$0.value==0 || ($0.value<32 && $0.value != 9 && $0.value != 10)}) else{close();return nil}
      let result=AsrText(text:text.trimmingCharacters(in:.whitespacesAndNewlines),final:finish)
      if finish{close()};return result
    } catch{close();return nil}
  }
  func close(){guard !closed else{return};closed=true;let old=stream;stream=nil;scratch.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)};old?.close()}
  deinit{close()}
}
