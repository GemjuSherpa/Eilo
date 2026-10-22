import Foundation

/// Owns queued request references; cancellation clears them even before worker scheduling.
/// Immutable String/allocator erasure cannot be certified by releasing references.
final class GenericReplyRequest {
  private let lock=NSLock();private var input:String,turns:[QwenTurn]
  init(latest:String,history:[QwenTurn]){input=latest;turns=history}
  var latest:String{lock.lock();defer{lock.unlock()};return input}
  var history:[QwenTurn]{lock.lock();defer{lock.unlock()};return turns}
  func cancel(){lock.lock();defer{lock.unlock()};input="";turns.removeAll()}
}
/// Native-only asynchronous seam. Real adapters are supplied explicitly; defaults
/// remain unavailable. A starter must schedule inference, never run it inline.
typealias GenericReplyStarter=(GenerationToken,GenericReplyRequest,@escaping(UnsafeBufferPointer<UInt8>)throws->Void,@escaping(LlmJobResult)->Void)->Bool
final class GenericSpokenTurn {
  private let controller:NativeController,token:GenerationToken,sink:any NativeClauseSink,starter:GenericReplyStarter,configured:Bool
  private var user="",reply=""
  private var submitted=false,queue:NativeClauseQueue?,output:NonThinkingOutput?
  private var pendingRequest:GenericReplyRequest?
  init(controller:NativeController,token:GenerationToken,sink:any NativeClauseSink,configured:Bool=false,starter:@escaping GenericReplyStarter={_,_,_,_ in false}){self.controller=controller;self.token=token;self.sink=sink;self.configured=configured;self.starter=starter}
  /// Final text from the bounded native ASR worker only; never ambient or JS text.
  /// Unknown confidence asks for clarification, never invents a runtime confidence.
  @discardableResult func submit(_ final:AsrText,confidence:Float?,ambiguous:Bool=false,overlap:Bool=false)->Bool {
    controller.lock.lock();defer{controller.lock.unlock()}
    guard configured,!submitted,final.final,controller.recognitionAllowed(token) else{return false}
    submitted=true
    let request:String
    switch RecognitionPolicy.decide(final.text,confidence:confidence,ambiguous:ambiguous,overlap:overlap){case .clarify:request=RecognitionPolicy.clarification;case .conversation(let text):request=text}
    guard let history=controller.genericContext(token) else{return false}
    user=request==RecognitionPolicy.clarification ? "":request
    guard controller.dispatch(.endpoint,token:token) else{return false}
    let policy=NativeSpeechPolicy(controller:controller,token:token,configured:true)
    guard let q=NativeClauseQueue.create(controller:controller,token:token,sink:sink,completed:{[weak self] t in if let self{self.controller.recordGenericTurn(t,user:self.user,reply:self.reply);self.user="";self.reply=""}},cleared:{[weak self] in self?.user="";self?.reply="";self?.output?.cancel();self?.pendingRequest?.cancel();self?.pendingRequest=nil},authorized:policy.allows) else{return false};queue=q
    let fixed = request==RecognitionPolicy.clarification ? request : (DangerPolicy.recognizes(request) ? DangerPolicy.response:CapabilityPolicy.response(request))
    if let fixed{reply=fixed;return q.enqueue(fixed) && q.seal()}
    let guardOutput=NonThinkingOutput(current:{[weak self] in self.map{!$0.token.cancelled} ?? false},emit:{[weak self] text in guard let self,self.reply.utf8.count+text.utf8.count<=4096 else{throw LlmFailure.unavailable};self.reply+=text;if !q.append(text){throw LlmFailure.unavailable}});output=guardOutput
    let ownedRequest=GenericReplyRequest(latest:request,history:history);pendingRequest=ownedRequest
    let accepted=starter(token,ownedRequest,{try guardOutput.append($0)},{[weak self] result in
      ownedRequest.cancel()
      guard let self else{return};self.controller.lock.lock();defer{self.controller.lock.unlock()}
      if self.pendingRequest === ownedRequest{self.pendingRequest=nil}
      guard !self.token.cancelled else{guardOutput.cancel();return}
      do {guard result == .completed else{throw LlmFailure.unavailable};try guardOutput.finish();guard q.seal() else{throw LlmFailure.unavailable}}
      catch{guardOutput.cancel();_ = self.controller.dispatch(.failure,failure:.unavailable,token:self.token)}
      self.output=nil
    })
    if !accepted{ownedRequest.cancel();if pendingRequest === ownedRequest{pendingRequest=nil};guardOutput.cancel();output=nil;_ = controller.dispatch(.failure,failure:.unavailable,token:token)}
    return accepted
  }
  /// Only confirmed native user speech plus a still-valid separation lease can replace.
  /// A transcript or VAD probability alone cannot authorize full-duplex capture.
  static func replacing(_ activation:InterruptionActivation,controller:NativeController,sink:any NativeClauseSink,configured:Bool=false,independentSpeechStillVerified:@escaping()->Bool={false},starter:@escaping GenericReplyStarter={_,_,_,_ in false})->GenericSpokenTurn? {
    guard configured,let token=activation.apply(controller,independentSpeechStillVerified:independentSpeechStillVerified) else{return nil}
    return GenericSpokenTurn(controller:controller,token:token,sink:sink,configured:true,starter:starter)
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
