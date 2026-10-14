import Foundation

/// Bounded English lexical screen plus exact native boundary responses.
/// Not a semantic classifier; public release still needs quality/safety review.
/// No permissions, network or model readiness can be granted by generated text.
final class NativeSpeechPolicy {
  static let version="eilo-speech-1"
  private let controller:NativeController,token:GenerationToken,configured:Bool
  init(controller:NativeController,token:GenerationToken,configured:Bool=false){self.controller=controller;self.token=token;self.configured=configured}
  func allows(_ expected:GenerationToken,_ text:String)->Bool {
    controller.lock.lock();defer{controller.lock.unlock()}
    guard configured,expected===token,controller.accepts(token),!controller.speakerRequired,[.thinking,.speaking].contains(controller.state),!text.isEmpty,text.utf8.count<=1024,
      text.unicodeScalars.allSatisfy({(32...126).contains($0.value) || [10,13,8216,8217,8220,8221].contains($0.value)}) else{return false}
    let fixed=[CapabilityPolicy.live,CapabilityPolicy.action,CapabilityPolicy.health,DangerPolicy.response,RecognitionPolicy.clarification,"I am Eilo, an AI companion.","Okay, take care."]
    let canonicalRefusals=["I cannot pretend to be human or promise secrecy.", "I cannot diagnose or assess your mental condition.", "I do not have feelings, but I can offer support and companionship.", "I cannot promise secrecy.", "I am Eilo, an AI companion. I cannot pretend to be human or promise secrecy.", "I am Eilo, an AI companion. I cannot diagnose or assess your mental condition.", "I am Eilo, an AI companion. I do not have feelings, but I can offer support and companionship.", "I am Eilo, an AI companion. I cannot promise secrecy."]
    if (fixed+canonicalRefusals).contains(text){return controller.accepts(token)}
    let words=text.lowercased().split(whereSeparator:{ !$0.isLetter && !$0.isNumber }).map(String.init)
    let risks:Set<String>=["diagnose","diagnosis","symptoms","prescribe","medicine","medication","pills","overdose","suicide","suicidal","kill","weapon","poison","bleach","hurt","harm","emergency","monitor","monitoring","ambulance","photo","camera","call","called","calling","browse","browsed","browsing","searched","news","confidential","confidentiality","secret","secrecy","human","conscious","consciousness","feelings","love"]
    guard !words.contains(where:risks.contains) else{return false}
    let normalized=" "+words.joined(separator:" ")+" "
    guard !["only support", "only need me", "depend on me", "trust only me", "do not tell anyone", "don t tell anyone", "promise", "guarantee", "i have feelings", "i feel your", "i will always", "i am your therapist"].contains(where:{normalized.contains($0)}) else{return false}
    return controller.accepts(token)
  }
}
