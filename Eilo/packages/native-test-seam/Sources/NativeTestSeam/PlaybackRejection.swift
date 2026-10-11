import Foundation
/// Conservative speaker/headphone fallback: reject known app output plus300 ms acoustic tail.
/// Full duplex requires independently verified echo separation. Metadata only, no PCM/text.
final class PlaybackRejection {
  private let lock=NSRecursiveLock(),now:()->UInt64
  private var output:GenerationToken?,until:UInt64=0,previous:UInt64?,invalidClock=false
  init(now:@escaping()->UInt64){self.now=now}
  func begin(_ token:GenerationToken){lock.lock();defer{lock.unlock()};if !token.cancelled{output=token}}
  @discardableResult func finish(_ token:GenerationToken)->Bool{lock.lock();defer{lock.unlock()};guard output === token else{return false};cancel();return true}
  func cancel(){lock.lock();defer{lock.unlock()};if output != nil{output=nil;let t=time();until=t>UInt64.max-300 ? UInt64.max:t+300}}
  private func time()->UInt64{let t=now();if let old=previous,t<old{invalidClock=true};previous=t;return t}
  var allowsAudio:Bool{lock.lock();defer{lock.unlock()};let t=time();return !invalidClock && output==nil && t>=until}
}
