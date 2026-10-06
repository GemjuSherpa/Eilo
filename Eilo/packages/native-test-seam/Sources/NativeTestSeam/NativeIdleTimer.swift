import Foundation
public protocol NativeClock { func milliseconds() -> UInt64 }
public protocol IdleCancellation { func cancel() }
public protocol IdleScheduler { func schedule(_ delayMilliseconds: UInt64, task: @escaping () -> Void) -> any IdleCancellation }
public struct MonotonicClock: NativeClock {
  public init() {}
  public func milliseconds() -> UInt64 { DispatchTime.now().uptimeNanoseconds / 1_000_000 }
}
private struct ScheduledIdle: IdleCancellation {
  let item: DispatchWorkItem
  func cancel() { item.cancel() }
}
public final class NativeIdleScheduler: IdleScheduler {
  private let queue=DispatchQueue(label:"Eilo-idle")
  public init() {}
  public func schedule(_ delayMilliseconds: UInt64, task: @escaping () -> Void) -> any IdleCancellation {
    let item=DispatchWorkItem(block:task)
    queue.asyncAfter(deadline:.now() + .milliseconds(Int(min(delayMilliseconds,60_000))),execute:item)
    return ScheduledIdle(item:item)
  }
}
