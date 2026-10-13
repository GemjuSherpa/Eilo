import Foundation
final class ContinuationChunk{let id:UUID,index:Int,plan:PromptPlan;init(id:UUID,index:Int,plan:PromptPlan){self.id=id;self.index=index;self.plan=plan}}
/// Native worker policy, not an automatic loop. Explicit longer request and fresh
/// native approval per chunk; <=4 chunks, <=256 tokens each, <=1024 total, context
/// <=4096 through the loaded-model budget builder. No ordinary app caller exists.
/// Stop publishes requestCancellation; worker returns clear borrowed references.
/// Revoked tokens reject later chunks. This does
/// not certify immutable String or vendor allocator erasure.
final class BoundedContinuation {
  private let token:GenerationToken,memoryAllowed:Bool,allowed:(GenerationToken)->Bool
  private var latest:String?,turns:[QwenTurn],recall:[String],pending:ContinuationChunk?,completed=0,closed=false
  private let cancellation=NSLock()
  private var cancelled=false
  private(set) var totalGenerated=0
  private init(token:GenerationToken,latest:String,history:[QwenTurn],recall:[String],memoryAllowed:Bool,allowed:@escaping(GenerationToken)->Bool){self.token=token;self.latest=latest;turns=history;self.recall=recall;self.memoryAllowed=memoryAllowed;self.allowed=allowed}
  static func create(controller:NativeController,token:GenerationToken,latest:String,history:[QwenTurn]=[],recall:[String]=[],requestedLonger:Bool=false,memoryAllowed:Bool=false,allowed:@escaping(GenerationToken)->Bool={_ in false})->BoundedContinuation?{
    guard requestedLonger,!token.cancelled,allowed(token),history.count<=32,recall.count<=32 else{return nil}
    let policy=BoundedContinuation(token:token,latest:latest,history:history,recall:recall,memoryAllowed:memoryAllowed,allowed:allowed)
    guard controller.prepareContinuation(token,cancel:{[weak policy] in policy?.requestCancellation()}) else{return nil};return policy
  }
  private var stopped:Bool{cancellation.lock();defer{cancellation.unlock()};return cancelled}
  private var current:Bool{!closed && !stopped && !token.cancelled && allowed(token) && !stopped && !token.cancelled}
  /// Fresh current loaded-model tokenizer for each explicit chunk request.
  func next(count:(String)throws->Int)->ContinuationChunk?{
    guard current else{cancel();return nil};guard pending==nil else{return nil};guard completed<4 else{cancel();return nil}
    do{
      guard let original=latest else{return nil}
      let request=completed==0 ? original:original+"\nContinue the requested answer from the previous approved chunk without repeating."
      let plan=try PromptBudget.build(latest:request,history:turns,recall:recall,memoryAllowed:memoryAllowed,count:count)
      if completed>0,plan.droppedHistory>=turns.count{cancel();return nil}
      turns.removeFirst(plan.droppedHistory);recall.removeLast(plan.droppedRecall)
      guard current else{cancel();return nil}
      let chunk=ContinuationChunk(id:UUID(),index:completed+1,plan:plan);pending=chunk;return chunk
    }catch{cancel();return nil}
  }
  /// Exact pending ID and native policy-approved text/count only. Acceptance never
  /// requests automatic continuation; caller must explicitly request another chunk.
  @discardableResult func complete(_ chunk:ContinuationChunk,text:String,generatedTokens:Int,approved:Bool=false)->Bool{
    guard current,pending===chunk,approved,(1...256).contains(generatedTokens),!text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty,text.utf8.count<=4096,!text.contains("\0"),!text.contains("<"),!text.contains(">") else{cancel();return false}
    totalGenerated+=generatedTokens;completed+=1;pending=nil
    if completed==4{cancel();return true}
    if turns.count==32{turns.removeFirst()};turns.append(QwenTurn(role:.assistant,text:text));guard current else{cancel();return false};return true
  }
  func requestCancellation(){cancellation.lock();cancelled=true;cancellation.unlock()}
  /// Worker-only cleanup; cancellation hook must not count or join.
  func cancel(){requestCancellation();closed=true;latest=nil;turns.removeAll();recall.removeAll();pending=nil}
}
