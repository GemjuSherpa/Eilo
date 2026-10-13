import Foundation

struct GenericReplyRequest{let latest:String,history:[QwenTurn]}
/// Native-only asynchronous seam. Real adapters are supplied explicitly; defaults
/// remain unavailable. A starter must schedule inference, never run it inline.
typealias GenericReplyStarter=(GenerationToken,GenericReplyRequest,@escaping(UnsafeBufferPointer<UInt8>)throws->Void,@escaping(LlmJobResult)->Void)->Bool
final class GenericSpokenTurn {
  private let controller:NativeController,token:GenerationToken,sink:any NativeClauseSink,starter:GenericReplyStarter,configured:Bool
  private var submitted=false,queue:NativeClauseQueue?,output:NonThinkingOutput?
  init(controller:NativeController,token:GenerationToken,sink:any NativeClauseSink,configured:Bool=false,starter:@escaping GenericReplyStarter={_,_,_,_ in false}){self.controller=controller;self.token=token;self.sink=sink;self.configured=configured;self.starter=starter}
  /// Final text from the bounded native ASR worker only; never ambient or JS text.
  /// Unknown confidence asks for clarification, never invents a runtime confidence.
  @discardableResult func submit(_ final:AsrText,confidence:Float?,ambiguous:Bool=false,overlap:Bool=false,history:[QwenTurn]=[])->Bool {
    controller.lock.lock();defer{controller.lock.unlock()}
    guard configured,!submitted,final.final,controller.recognitionAllowed(token) else{return false}
    submitted=true
    let request:String
    switch RecognitionPolicy.decide(final.text,confidence:confidence,ambiguous:ambiguous,overlap:overlap){case .clarify:request=RecognitionPolicy.clarification;case .conversation(let text):request=text}
    guard controller.dispatch(.endpoint,token:token) else{return false}
    let policy=NativeSpeechPolicy(controller:controller,token:token,configured:true)
    guard let q=NativeClauseQueue.create(controller:controller,token:token,sink:sink,authorized:policy.allows) else{return false};queue=q
    let fixed = request==RecognitionPolicy.clarification ? request : (DangerPolicy.recognizes(request) ? DangerPolicy.response:CapabilityPolicy.response(request))
    if let fixed{return q.enqueue(fixed) && q.seal()}
    let guardOutput=NonThinkingOutput(current:{[weak self] in self.map{!$0.token.cancelled} ?? false},emit:{text in if !q.append(text){throw LlmFailure.unavailable}});output=guardOutput
    let accepted=starter(token,GenericReplyRequest(latest:request,history:history),{try guardOutput.append($0)},{[weak self] result in
      guard let self else{return};self.controller.lock.lock();defer{self.controller.lock.unlock()}
      guard !self.token.cancelled else{guardOutput.cancel();return}
      do {guard result == .completed else{throw LlmFailure.unavailable};try guardOutput.finish();guard q.seal() else{throw LlmFailure.unavailable}}
      catch{guardOutput.cancel();_ = self.controller.dispatch(.failure,failure:.unavailable,token:self.token)}
      self.output=nil
    })
    if !accepted{guardOutput.cancel();_ = controller.dispatch(.failure,failure:.unavailable,token:token)}
    return accepted
  }
  static func localReply(controller:NativeController,store:PackStore,selection:LlmPackSelection,api:NativeLlmAPI = .linked,limit:Int=96)->GenericReplyStarter {
    {token,request,consume,completion in
      do {
        // Small bounded placeholder owns no personal content; plan uses loaded tokenizer.
        var bytes=Array("Native generic request".utf8);defer{bytes.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
        let owned=try bytes.withUnsafeBufferPointer{try LlmOwnedPrompt($0)}
        return LlmControllerJob.submit(controller:controller,token:token,store:store,selection:selection,prompt:owned,outputLimit:limit,api:api,request:request,completion:completion,consume:consume) != nil
      }catch{return false}
    }
  }
}
