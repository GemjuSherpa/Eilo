import Foundation
enum RecognitionDecision {
  case clarify
  /// Conversational input only. Recognition does not confirm a personal memory fact.
  case conversation(String)
}
enum RecognitionPolicy {
  static let clarification="Could you say that again?"
  static func decide(_ text:String,confidence:Float?,ambiguous:Bool=false,overlap:Bool=false)->RecognitionDecision {
    let value=text.trimmingCharacters(in:.whitespacesAndNewlines)
    guard !value.isEmpty,value.utf8.count<=4096,
      !value.unicodeScalars.contains(where:{$0.value==0 || ($0.value<32 && $0.value != 9 && $0.value != 10)}),
      let score=confidence,score.isFinite,(0.85...1).contains(score),!ambiguous,!overlap else{return .clarify}
    return .conversation(value)
  }
}
