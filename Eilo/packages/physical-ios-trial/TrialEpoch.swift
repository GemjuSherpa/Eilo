import Foundation

/// Trial-owned queued callbacks are revoked by Stop, lock or a newer operation.
final class TrialEpoch: @unchecked Sendable {
  private let lock=NSLock()
  private var epoch=UUID(),active=false
  func begin()->UUID{lock.lock();defer{lock.unlock()};epoch=UUID();active=true;return epoch}
  func cancel(){lock.lock();defer{lock.unlock()};epoch=UUID();active=false}
  func current(_ ticket:UUID)->Bool{lock.lock();defer{lock.unlock()};return active && epoch==ticket}
}
