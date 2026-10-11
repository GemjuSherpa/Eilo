import Foundation
/// Native-worker VAD evidence only. Playback separation is a separately verified native route.
/// Neither energy nor a transcript can grant independent-user evidence by default.
final class ConfirmedSpeechInterruption {
  private let token:GenerationToken
  private var high=0,closed=false
  init(_ token:GenerationToken){self.token=token}
  func advance(_ probability:Float,independentUserSpeech:Bool,samples:Int=320)->InterruptionActivation? {
    guard !closed,!token.cancelled else{return nil}
    guard samples==320,probability.isFinite,(0...1).contains(probability) else{closed=true;high=0;return nil}
    guard independentUserSpeech,probability>=0.8 else{high=0;return nil}
    high+=samples;guard high>=2560 else{return nil};closed=true;high=0;return InterruptionActivation(token)
  }
}
final class InterruptionActivation {
  private let token:GenerationToken
  fileprivate init(_ token:GenerationToken){self.token=token}
  func apply(_ controller:NativeController,independentSpeechStillVerified:()->Bool)->GenerationToken?{controller.interruptReply(token,independentSpeechStillVerified:independentSpeechStillVerified)}
}
