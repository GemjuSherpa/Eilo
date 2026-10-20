import Foundation
import CryptoKit

/// One generic frozen answer, volatile until human review. No audio or persisted output.
enum TrialModelQuality {
  struct Reply {let prompt,rubric,answer:String}
  private struct Corpus:Decodable{struct Prompt:Decodable{let id,text,quality_rubric:String};let prompts:[Prompt]}
  static func run(assets:URL,store:PackStore,selection:LlmPackSelection,fixture:Int,cancellation:TrialModelCancellation,allowed:@escaping()->Bool)throws->Reply{
    let data=try Data(contentsOf:assets.appendingPathComponent("model-comparison-fixtures.json"))
    guard allowed(),(1...6).contains(fixture),SHA256.hash(data:data).map({String(format:"%02x",$0)}).joined()==TrialModelDiagnostic.fixtureDigest else{throw LlmFailure.unavailable}
    let corpus=try JSONDecoder().decode(Corpus.self,from:data)
    guard corpus.prompts.map({$0.id})==(1...6).map({String(format:"compare-%02d",$0)}) else{throw LlmFailure.unavailable}
    let prompt=corpus.prompts[fixture-1]
    let lease=try LlmPackLease.resolve(store:store,selection:selection);defer{lease.close();cancellation.clear()}
    let stream=try lease.openStream(allowed:allowed,threads:2,created:{cancellation.publish($0)});defer{stream.close()}
    let plan=try PromptBudget.build(latest:prompt.text,count:{try stream.countTokens($0)})
    var input=Array(plan.text.utf8),output=[UInt8]()
    defer{input.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)};output.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
    try input.withUnsafeBufferPointer{try stream.begin($0,outputLimit:256)}
    var oversized=false,pieces=0
    while try stream.withNextPiece({piece in
      pieces+=1
      if output.count+piece.count<=16384{output.append(contentsOf:piece)}else{oversized=true}
    }){guard allowed(),!oversized,pieces<=256 else{throw LlmFailure.unavailable}}
    guard allowed(),!oversized,pieces>0 else{throw LlmFailure.unavailable}
    let answer=try TrialModelQualityText.decode(output)
    guard allowed() else{throw LlmFailure.cancelled}
    return Reply(prompt:prompt.text,rubric:prompt.quality_rubric,answer:answer)
  }
}
