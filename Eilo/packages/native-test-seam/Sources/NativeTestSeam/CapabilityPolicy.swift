import Foundation

/// Narrow English request routing. No action/permission/provider dependencies.
/// Unknown requests remain uncertain model replies, never an action instruction.
enum CapabilityPolicy {
  static let version = "eilo-capabilities-1"
  static let rules = " Be honest about uncertainty; ask a short clarification when needed. You cannot browse live news, make calls, take photos, control other apps, diagnose conditions, monitor danger or contact emergency services. Never claim you performed these actions or request new permissions. For current facts explain that you cannot verify live information. For health concerns encourage qualified professional help without a diagnosis."
  static let live = "I cannot verify live information or browse current news. Please check a trusted current source."
  static let action = "I cannot make calls, take photos or control other apps. You can use your phone's controls yourself."
  static let health = "I cannot diagnose a condition. A qualified health professional can help with health concerns."
  static func response(_ input:String)->String? {
    let words = input.lowercased().split(whereSeparator:{ !$0.isLetter && !$0.isNumber }).map(String.init)
    let text = " " + words.joined(separator:" ") + " "
    if [" diagnose "," diagnosis "," symptoms "].contains(where:text.contains){return health}
    if [" call "," phone "," photograph "," photo "," camera "," open app "," launch app "].contains(where:text.contains){return action}
    if [" latest "," current news "," news today "," live news "," browse "," search the web "].contains(where:text.contains){return live}
    return nil
  }
}
