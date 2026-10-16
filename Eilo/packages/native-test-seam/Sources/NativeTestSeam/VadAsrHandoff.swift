import Foundation

enum VadAsrFinal { case metadata, recognized(AsrText), invalid }

/// One native worker's bounded utterance owner. No ASR stream opens for silence/early EOF.
/// Retains <=30 s of 16 kHz PCM; only exact VAD-consumed prefixes are copied. No JS/file/log sink.
final class VadAsrHandoff {
  private let token:GenerationToken,allowed:()->Bool,open:()throws->AsrStream
  private var pcm=[Float](repeating:0,count:480000)
  private var count=0,closed=false
  init(token:GenerationToken,allowed:@escaping ()->Bool,open:@escaping ()throws->AsrStream) {
    self.token=token;self.allowed=allowed;self.open=open
  }
  var retainedSamples:Int {count}
  private var valid:Bool {!closed && !token.cancelled && allowed()}
  func append(_ input:UnsafeBufferPointer<Float>,consumed:Int,startSample:Int)->Bool {
    guard valid,startSample==count,(1...1600).contains(input.count),(1...input.count).contains(consumed),
      count<=480000-consumed,input.allSatisfy({$0.isFinite && (-1...1).contains($0)}) else{close();return false}
    for i in 0..<consumed{pcm[count+i]=input[i]};count+=consumed
    guard valid else{close();return false};return true
  }
  func finish(_ outcome:VadCaptureOutcome)->VadAsrFinal {
    defer{close()}
    guard valid,outcome.totalSamples==count,(0...1600).contains(outcome.lastChunkConsumed) else{return .invalid}
    switch outcome.result {
    case .noSpeech: return count==80000 ? .metadata:.invalid
    case .incomplete: return .metadata
    case .complete,.limit:
      guard count>0,outcome.result != .limit || count==480000 else{return .invalid}
    default:return .invalid
    }
    let asr=StreamingAsr(token,allowed:allowed,open:open);defer{asr.close()}
    for offset in stride(from:0,to:count,by:1600) {
      guard valid,pcm.withUnsafeBufferPointer({asr.accept(UnsafeBufferPointer(rebasing:$0[offset..<min(count,offset+1600)]))}) else{return .invalid}
    }
    guard valid,let text=asr.poll(finish:true),text.final,valid else{return .invalid}
    return .recognized(text)
  }
  func close(){guard !closed else{return};closed=true;pcm.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)};count=0}
  deinit{close()}
}
