import Foundation
public enum ControllerState: String, CaseIterable, Sendable {
  case setup, permissionRequired = "permission_required", stopped, standby, capturing = "listening", thinking, speaking, paused, error
}
public enum ControllerEvent: CaseIterable, Sendable {
  case setupRequired, ready, start, speechDetected, endpoint, speechReady, playbackFinished, pause, resume, stop, failure
}
/// Sole native state authority; serialized observations and effects.
public final class NativeController: @unchecked Sendable {
  let lock = NSRecursiveLock()
  let diagnostics: SafeDiagnostics
  var currentState: ControllerState = .stopped
  var currentError: SafeError?
  public init(diagnostics: SafeDiagnostics = SafeDiagnostics()) { self.diagnostics = diagnostics }
  public var state: ControllerState { lock.lock(); defer { lock.unlock() }; return currentState }
  public var error: SafeError? { lock.lock(); defer { lock.unlock() }; return currentError }
  @discardableResult public func dispatch(_ event: ControllerEvent, failure: SafeError = .unexpected) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard let next = Self.nextState(currentState, event) else { return false }
    currentState = next; currentError = next == .error ? failure : nil
    if next == .error { diagnostics.record(.controller, failure, .error) }
    return true
  }
  public static func nextState(_ state: ControllerState, _ event: ControllerEvent) -> ControllerState? {
    switch event {
    case .stop: return .stopped
    case .failure: return .error
    case .setupRequired: return state == .stopped ? .setup : nil
    case .ready: return [.setup, .error].contains(state) ? .stopped : nil
    case .start: return state == .stopped ? .standby : nil
    case .speechDetected: return state == .standby ? .capturing : nil
    case .endpoint: return state == .capturing ? .thinking : nil
    case .speechReady: return state == .thinking ? .speaking : nil
    case .playbackFinished: return state == .speaking ? .standby : nil
    case .pause: return [.standby, .capturing, .thinking, .speaking].contains(state) ? .paused : nil
    case .resume: return state == .paused ? .standby : nil
    }
  }
}
