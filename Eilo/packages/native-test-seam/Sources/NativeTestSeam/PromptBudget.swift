import Foundation
struct PromptPlan{let text:String,promptTokens:Int,recalledTokens:Int,outputLimit:Int,droppedHistory:Int,droppedRecall:Int}
/// Current loaded-model tokenizer only; default unavailable. Never truncate rules
/// or latest utterance. Drop oldest context then lowest-priority recall units.
enum PromptBudget {
  static func recallText(_ units:[String])->String{"Quoted context:\n"+units.joined(separator:"\n")}
  static func build(latest:String,history:[QwenTurn]=[],recall:[String]=[],outputLimit:Int=256,
                    count:(String)throws->Int={_ in throw QwenPromptFailure.unavailable})throws->PromptPlan{
    guard (1...256).contains(outputLimit),history.count<=32,recall.count<=32,!latest.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty else{throw QwenPromptFailure.unavailable}
    _ = try QwenTemplate.data(latest);for turn in history{_ = try QwenTemplate.data(turn.text)};for unit in recall{_ = try QwenTemplate.data(unit)}
    var turns=history,units=recall
    func measured(_ text:String)throws->Int{let n=try count(text);guard (1...32768).contains(n) else{throw QwenPromptFailure.unavailable};return n}
    func recallCount()throws->Int{guard !units.isEmpty else{return 0};guard let text=try? QwenTemplate.data(recallText(units)) else{return 32768};return try measured(text)}
    while !units.isEmpty,try recallCount()>512{units.removeLast()}
    while true{
      let context=turns+(units.isEmpty ? []:[QwenTurn(role:.user,text:recallText(units))])
      let text=try? QwenTemplate.render(latest:latest,history:context)
      let n=try text.map{try measured($0)} ?? 32768
      if let text,n+outputLimit<=4096{return PromptPlan(text:text,promptTokens:n,recalledTokens:try recallCount(),outputLimit:outputLimit,droppedHistory:history.count-turns.count,droppedRecall:recall.count-units.count)}
      if !turns.isEmpty{turns.removeFirst()}else if !units.isEmpty{units.removeLast()}else{throw QwenPromptFailure.unavailable}
    }
  }
}
