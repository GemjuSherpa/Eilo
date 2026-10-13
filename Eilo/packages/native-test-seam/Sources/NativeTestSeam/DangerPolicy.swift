import Foundation

/// Conservative English signal routing, not diagnosis or a risk assessment.
/// Quoted/negated/history mentions also receive conditional support; no location.
enum DangerPolicy {
  static let version="eilo-danger-1"
  static let rules=" For explicit immediate danger, prioritize a brief supportive response directing the user to contact local emergency services now and a trusted person nearby. You cannot contact help or monitor safety. Do not ask for location or describe harmful methods. Never offer a safety guarantee."
  static let response="I am sorry you are facing this. If you or someone else is in immediate danger, contact your local emergency services now; in Australia, call triple zero. If you can, ask someone you trust nearby to stay with you and help. I cannot contact help or monitor your safety."
  static func recognizes(_ input:String)->Bool {
    let text=" "+input.lowercased().split(whereSeparator:{ !$0.isLetter && !$0.isNumber }).joined(separator:" ")+" "
    return ["kill myself", "end my life", "hurt myself", "harm myself", "suicide", "suicidal", "kill someone", "hurt someone", "immediate danger", "not safe", "being attacked", "overdose", "cannot breathe", "can t breathe"].contains{ text.contains(" "+$0+" ") }
  }
}
