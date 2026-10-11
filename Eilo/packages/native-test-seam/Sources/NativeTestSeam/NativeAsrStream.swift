import Foundation
#if canImport(CEiloAsr)
import CEiloAsr
#endif
enum AsrFailure:Error{case unavailable}
struct NativeAsrAPI {
  let create:(String)->OpaquePointer?
  let accept:(OpaquePointer,UnsafeBufferPointer<Float>)->Int32
  let text:(OpaquePointer,Bool,UnsafeMutableBufferPointer<CChar>)->Int32
  let destroy:(OpaquePointer)->Void
  static var linked:NativeAsrAPI {
    #if canImport(CEiloAsr) && DEBUG && EILO_ASR_EVALUATION
    return NativeAsrAPI(create:{$0.withCString{eilo_asr_create($0)}},accept:{eilo_asr_accept($0,$1.baseAddress,Int32($1.count))},text:{eilo_asr_text($0,$1 ? 1:0,$2.baseAddress,Int32($2.count))},destroy:{eilo_asr_destroy($0)})
    #else
    return NativeAsrAPI(create:{_ in nil},accept:{_,_ in -1},text:{_,_,_ in -1},destroy:{_ in})
    #endif
  }
}
/// Serialized inference-worker binding. Paths/lease are native capabilities, not bridge parameters.
final class NativeAsrStream:AsrStream {
  private var handle:OpaquePointer?
  private let api:NativeAsrAPI,verified:()->Bool
  private var textBuffer=[CChar](repeating:0,count:4097)
  init(directory:String,verified:@escaping ()->Bool,api:NativeAsrAPI = .linked)throws{
    self.api=api;self.verified=verified
    guard directory.hasPrefix("/"),directory.utf8.count<=4096,!directory.utf8.contains(0),verified(),let h=api.create(directory) else{throw AsrFailure.unavailable}
    guard verified() else{api.destroy(h);throw AsrFailure.unavailable};handle=h
  }
  func accept(_ pcm:UnsafeBufferPointer<Float>)throws{guard let h=handle,verified(),(1...1600).contains(pcm.count),pcm.allSatisfy({$0.isFinite && (-1...1).contains($0)}),api.accept(h,pcm)==0,verified() else{close();throw AsrFailure.unavailable}}
  func text(finish:Bool)throws->String{
    defer{textBuffer.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
    guard let h=handle,verified(),textBuffer.withUnsafeMutableBufferPointer({api.text(h,finish,$0)})==0,verified(),let end=textBuffer.firstIndex(of:0),let text=String(bytes:textBuffer[0..<end].map{UInt8(bitPattern:$0)},encoding:.utf8) else{close();throw AsrFailure.unavailable}
    return text
  }
  func close(){let old=handle;handle=nil;textBuffer.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)};if let old{api.destroy(old)}}
  deinit{close()}
}
