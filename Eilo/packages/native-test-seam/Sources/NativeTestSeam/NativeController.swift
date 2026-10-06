import Foundation
public enum ControllerState: String, CaseIterable, Sendable {
  case setup, permissionRequired = "permission_required", stopped, standby, capturing = "listening", thinking, speaking, paused, error
}
public enum ControllerEvent: CaseIterable, Sendable {
  case setupRequired, ready, start, speechDetected, endpoint, speechReady, playbackFinished, pause, resume, stop, failure
}
/// Effects are synchronous/nonblocking/idempotent. Async callbacks return through the controller.
public protocol ControllerEffects: AnyObject {
  func playClause(_ clause: String) throws
  func cancelWork() throws
  func releaseCapture() throws
  func clearVolatileContext() throws
}
public final class NoopControllerEffects: ControllerEffects {
  public init() {}
  public func playClause(_ clause: String) throws {}
  public func cancelWork() throws {}
  public func releaseCapture() throws {}
  public func clearVolatileContext() throws {}
}
public final class GenerationToken: @unchecked Sendable {
  public let sessionID: UUID
  public let operationID: UUID
  public let generation: UInt64
  private let lock = NSLock()
  private var revoked = false
  public var cancelled: Bool { lock.lock(); defer { lock.unlock() }; return revoked }
  fileprivate func cancel() { lock.lock(); defer { lock.unlock() }; revoked = true }
  fileprivate init(_ session: UUID, _ generation: UInt64) { sessionID = session; operationID = UUID(); self.generation = generation }
}
/// Sole native state authority; serialized observations and effects.
public final class NativeController: @unchecked Sendable {
  let lock = NSRecursiveLock()
  let diagnostics: SafeDiagnostics
  let effects: any ControllerEffects
  var sessionID = UUID()
  var generation: UInt64 = 0
  var activeToken: GenerationToken?
  public var token: GenerationToken? { lock.lock(); defer { lock.unlock() }; return activeToken }
  func invalidateGeneration() {
    activeToken?.cancel(); activeToken = nil
    if generation == 9_007_199_254_740_991 { sessionID = UUID(); generation = 0 } else { generation += 1 }
  }
  func issueGeneration() { invalidateGeneration(); activeToken = GenerationToken(sessionID,generation) }
  func accepts(_ token: GenerationToken?) -> Bool { guard let token else { return false }; return token === activeToken && !token.cancelled }
  var currentState: ControllerState = .stopped
  var currentError: SafeError?
  public init(diagnostics: SafeDiagnostics = SafeDiagnostics(), effects: any ControllerEffects = NoopControllerEffects()) { self.diagnostics = diagnostics; self.effects = effects }
  public var state: ControllerState { lock.lock(); defer { lock.unlock() }; return currentState }
  public var error: SafeError? { lock.lock(); defer { lock.unlock() }; return currentError }
  @discardableResult public func dispatch(_ event: ControllerEvent, failure: SafeError = .unexpected, token: GenerationToken? = nil) -> Bool {
    lock.lock(); defer { lock.unlock() }
    if event == .stop { return stop() }
    if [.speechDetected,.endpoint,.speechReady,.playbackFinished,.failure].contains(event) && !accepts(token) { return false }
    guard let next = Self.nextState(currentState, event) else { return false }
    if event == .start || event == .speechDetected || event == .playbackFinished || event == .resume { issueGeneration() }
    if (event == .pause || event == .failure) && !stop() { return false }
    currentState = next; currentError = next == .error ? failure : nil
    if next == .error { diagnostics.record(.controller, failure, .error) }
    return true
  }
  @discardableResult public func releaseSpeech(_ token: GenerationToken, clause: String) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard accepts(token), [.thinking,.speaking].contains(currentState) else { return false }
    do { try effects.playClause(clause); guard accepts(token) else { return false }; currentState = .speaking; return true }
    catch { stop(); currentState = .error; currentError = .unexpected; diagnostics.record(.speech,.unexpected,.error); return false }
  }
  public func cancelGeneration() {
    lock.lock(); defer { lock.unlock() }; invalidateGeneration()
    do { try effects.cancelWork() } catch { stop(); currentState = .error; currentError = .unexpected; return }
    if [.capturing,.thinking,.speaking].contains(currentState) { currentState = .standby; issueGeneration() }
  }
  @discardableResult public func stop() -> Bool {
    lock.lock(); defer { lock.unlock() }
    invalidateGeneration()
    currentState = .stopped; currentError = nil
    var failed = false
    let cleanups: [() throws -> Void] = [effects.cancelWork, effects.releaseCapture, effects.clearVolatileContext]
    for cleanup in cleanups { do { try cleanup() } catch { failed = true } }
    diagnostics.clear()
    if failed { currentState = .error; currentError = .unexpected; diagnostics.record(.controller,.unexpected,.error) }
    return !failed
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
