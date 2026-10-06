import Foundation
public enum ControllerState: String, CaseIterable, Sendable {
  case setup, permissionRequired = "permission_required", stopped, standby, capturing = "listening", thinking, speaking, paused, error
}
public enum ControllerEvent: CaseIterable, Sendable {
  case setupRequired, ready, start, speechDetected, endpoint, speechReady, playbackFinished, pause, resume, stop, failure
}
/// Effects are synchronous/nonblocking/idempotent. Async callbacks return through the controller.
public protocol ControllerEffects: AnyObject {
  func startCapture() throws -> Bool
  func beginCapture(completion: @escaping (Bool) -> Void, failure: @escaping () -> Void) throws
  func playClause(_ clause: String) throws
  func cancelWork() throws
  func releaseCapture() throws
  func clearVolatileContext() throws
}
public extension ControllerEffects {
  func beginCapture(completion: @escaping (Bool) -> Void, failure: @escaping () -> Void) throws { completion(try startCapture()) }
}
public final class NoopControllerEffects: ControllerEffects {
  public init() {}
  public func startCapture() throws -> Bool { false }
  public func playClause(_ clause: String) throws {}
  public func cancelWork() throws {}
  public func releaseCapture() throws {}
  public func clearVolatileContext() throws {}
}
public final class GenerationToken: @unchecked Sendable {
  public let sessionID: UUID
  public let operationID: UUID
  public let privacyEpoch: UInt64
  public let generation: UInt64
  private let lock = NSLock()
  private var revoked = false
  public var cancelled: Bool { lock.lock(); defer { lock.unlock() }; return revoked }
  fileprivate func cancel() { lock.lock(); defer { lock.unlock() }; revoked = true }
  fileprivate init(_ session: UUID, _ generation: UInt64, _ epoch: UInt64) { sessionID = session; operationID = UUID(); self.generation = generation; privacyEpoch = epoch }
}
public enum PrivacyChange { case lock, unlock, privateSession, historySession, identityReset, deleteAll }
public enum PrivateEffect { case readMemory, commitHistory, displayPrivate }
public protocol PrivateEffectGate { func allows(_ effect: PrivateEffect) -> Bool }
public struct DeniedPrivateEffectGate: PrivateEffectGate {
  public init() {}
  public func allows(_ effect: PrivateEffect) -> Bool { false }
}
/// Sole native state authority; serialized observations and effects.
public final class NativeController: @unchecked Sendable {
  let lock = NSRecursiveLock()
  let diagnostics: SafeDiagnostics
  let effects: any ControllerEffects
  let permission: any MicrophonePermissionAdapter
  let models: any ModelReadinessAdapter
  public var modelStatus: ModelStatus { models.status() }
  public func modelsChanged() { lock.lock();defer { lock.unlock() };if modelStatus != .ready { stop();if currentState == .stopped { currentState = .setup } } else if currentState == .setup { currentState = .stopped } }
  var speakerRequired=false
  public var speakerConfirmationRequired: Bool { lock.lock();defer { lock.unlock() };return speakerRequired }
  public func routeDisconnected() { lock.lock();defer { lock.unlock() };speakerRequired=true;stop() }
  @discardableResult public func confirmSpeaker() -> Bool { lock.lock();defer { lock.unlock() };guard !locked else { return false };speakerRequired=false;return true }
  var stopping=false
  var startIntent: UUID?
  var capturePending=false
  var captureIntent: UUID?
  var permissionPrompted=false
  func permissionGranted() -> Bool { permission.status() == .granted }
  public func permissionChanged() { lock.lock(); defer { lock.unlock() }; if !permissionGranted() { stop() } }
  func start() -> Bool {
    guard !stopping, startIntent == nil, !locked, [.stopped,.permissionRequired,.paused].contains(currentState) else { return false }
    guard modelStatus == .ready else { modelsChanged();return false }
    let intent=UUID(); startIntent=intent
    switch permission.status() {
    case .granted: return completeStart(intent,.granted)
    case .notRequested:
      guard !permissionPrompted else { startIntent=nil; currentState = .permissionRequired; return false }
      permissionPrompted=true; currentState = .permissionRequired
      permission.request { [weak self] result in self?.completeStart(intent,result) }; return true
    case .denied: startIntent=nil; currentState = .permissionRequired; currentError=nil; return false
    case .unavailable: stop(); currentState = .error; currentError = .unavailable; return false
    }
  }
  @discardableResult func completeStart(_ intent: UUID, _ result: MicrophonePermission) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard startIntent == intent, !capturePending, !locked else { return false }
    guard modelStatus == .ready else { modelsChanged();return false }
    guard result == .granted, permissionGranted() else { startIntent=nil; currentState = .permissionRequired; currentError=nil; return false }
    capturePending=true
    let immediate=CaptureCompletionResult()
    do {
      try effects.beginCapture(completion: { [weak self] opened in immediate.set(self?.finishCapture(intent,opened) ?? false) }, failure: { [weak self] in self?.captureFailed(intent) })
      return immediate.get() ?? true
    } catch { captureFailed(intent); return false }
  }
  func finishCapture(_ intent: UUID, _ opened: Bool) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard startIntent == intent, capturePending else { return false }
    guard opened, !locked, [.stopped,.permissionRequired,.paused].contains(currentState), permissionGranted(), modelStatus == .ready else {
      stop(); if !opened { currentState = .error; currentError = .unavailable }; return false
    }
    guard startIntent == intent, capturePending else { return false }
    startIntent=nil; capturePending=false; captureIntent=intent
    issueGeneration(); currentState = .standby; currentError=nil; return true
  }
  func captureFailed(_ intent: UUID) {
    lock.lock(); defer { lock.unlock() }
    guard startIntent == intent || captureIntent == intent else { return }
    stop(); currentState = .error; currentError = .unavailable; diagnostics.record(.capture,.unavailable,.error)
  }
  let clock: any NativeClock
  let scheduler: any IdleScheduler
  var idleTask: (any IdleCancellation)?
  var idleStarted: UInt64?
  var hasConversation=false
  func clearIdle() { let previous=idleTask; idleTask=nil; idleStarted=nil; previous?.cancel() }
  func updateIdle() {
    clearIdle()
    if currentState == .standby && hasConversation, let expected=activeToken {
      idleStarted=clock.milliseconds()
      idleTask=scheduler.schedule(60_000) { [weak self] in self?.expireIdle(expected) }
    }
  }
  func expireIdle(_ expected: GenerationToken) {
    lock.lock(); defer { lock.unlock() }
    guard accepts(expected), currentState == .standby, let started=idleStarted else { return }
    let now=clock.milliseconds()
    let elapsed=now >= started ? now-started : 0
    if elapsed < 60_000 { idleTask=scheduler.schedule(60_000-elapsed) { [weak self] in self?.expireIdle(expected) }; return }
    endSessionPreservingCapture()
  }
  @discardableResult func endSessionPreservingCapture() -> Bool {
    guard permissionGranted() else { stop(); return false }
    clearIdle(); invalidateGeneration(); hasConversation=false
    let expectedGeneration=generation, expectedEpoch=privacyEpoch
    do {
      try effects.cancelWork(); try effects.clearVolatileContext()
      guard generation == expectedGeneration, privacyEpoch == expectedEpoch else { return false }
      sessionID=UUID(); currentState = .standby; issueGeneration(); return true
    } catch { stop(); currentState = .error; currentError = .unexpected; diagnostics.record(.controller,.unexpected,.error); return false }
  }
  var sessionID = UUID()
  let privateGate: any PrivateEffectGate
  var privacyEpoch: UInt64 = 0
  var locked = false
  var privateSession = true
  var stoppedOperationID=UUID()
  var generation: UInt64 = 0
  var activeToken: GenerationToken?
  public var token: GenerationToken? { lock.lock(); defer { lock.unlock() }; return activeToken }
  func invalidateGeneration() {
    activeToken?.cancel(); activeToken = nil; stoppedOperationID=UUID()
    if generation == 9_007_199_254_740_991 { sessionID = UUID(); generation = 0 } else { generation += 1 }
  }
  func issueGeneration() { invalidateGeneration(); activeToken = GenerationToken(sessionID,generation,privacyEpoch) }
  func accepts(_ token: GenerationToken?) -> Bool {
    guard let token, token === activeToken, !token.cancelled, token.privacyEpoch == privacyEpoch else { return false }
    guard permissionGranted() else { stop(); return false }
    guard modelStatus == .ready else { modelsChanged();return false }
    return token === activeToken && !token.cancelled && token.privacyEpoch==privacyEpoch
  }
  var currentState: ControllerState = .stopped
  var currentError: SafeError?
  public init(diagnostics: SafeDiagnostics = SafeDiagnostics(), effects: any ControllerEffects = NoopControllerEffects(), privateGate: any PrivateEffectGate = DeniedPrivateEffectGate(), clock: any NativeClock = MonotonicClock(), scheduler: any IdleScheduler = NativeIdleScheduler(), permission: any MicrophonePermissionAdapter = UnavailablePermissionAdapter(), models: any ModelReadinessAdapter = MissingModelReadiness()) { self.diagnostics = diagnostics; self.effects = effects; self.privateGate = privateGate; self.clock=clock; self.scheduler=scheduler; self.permission=permission;self.models=models }
  /// Metadata only; no native content/keys/errors can enter this presentation snapshot.
  public func snapshot() -> [String: Any] {
    lock.lock(); defer { lock.unlock() }
    var result: [String:Any] = ["modelStatus":modelStatus.rawValue,"version":1,"state":currentState.rawValue,"sessionId":sessionID.uuidString.lowercased(),"operationId":(activeToken?.operationID ?? stoppedOperationID).uuidString.lowercased(),"generation":generation,"privacyEpoch":privacyEpoch]
    if currentState == .error { result["errorCode"] = currentError == .permissionDenied ? "permission_denied" : (currentError ?? .unexpected).rawValue }
    return result
  }
  public var state: ControllerState { lock.lock(); defer { lock.unlock() }; return currentState }
  public var error: SafeError? { lock.lock(); defer { lock.unlock() }; return currentError }
  @discardableResult public func dispatch(_ event: ControllerEvent, failure: SafeError = .unexpected, token: GenerationToken? = nil) -> Bool {
    lock.lock(); defer { lock.unlock() }
    if stopping && event != .stop { return false }
    if locked && [.start,.resume].contains(event) { return false }
    if event == .stop { return stop() }
    if event == .resume && currentState != .paused { return false }
    if event == .start && currentState == .paused { return false }
    if event == .start || event == .resume { return start() }
    if [.speechDetected,.endpoint,.speechReady,.playbackFinished,.failure].contains(event) && !accepts(token) { return false }
    guard let next = Self.nextState(currentState, event) else { return false }
    if event == .start || event == .speechDetected || event == .playbackFinished || event == .resume { issueGeneration() }
    if (event == .pause || event == .failure) && !stop() { return false }
    currentState = next
    if event == .speechDetected { hasConversation=true }
    updateIdle()
    currentError = next == .error ? failure : nil
    if next == .error { diagnostics.record(.controller, failure, .error) }
    return true
  }
  /// Native ASR input is consumed synchronously, never retained/bridged/logged.
  @discardableResult public func recognizedCommand(_ text: String, token: GenerationToken) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard accepts(token), text.utf8.count <= 64, [.standby,.capturing,.thinking,.speaking].contains(currentState) else { return false }
    switch text.trimmingCharacters(in:.whitespacesAndNewlines).lowercased() {
    case "stop listening": return stop()
    case "end conversation": return endConversation()
    default: return false
    }
  }
  @discardableResult public func endConversation() -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard [.standby,.capturing,.thinking,.speaking].contains(currentState) else { return false }
    return endSessionPreservingCapture()
  }
  @discardableResult public func privacyTransition(_ change: PrivacyChange) -> Bool {
    lock.lock(); defer { lock.unlock() }
    if privacyEpoch == 9_007_199_254_740_991 { sessionID = UUID(); privacyEpoch = 0 } else { privacyEpoch += 1 }
    switch change {
    case .lock: locked = true
    case .unlock: locked = false
    case .privateSession,.identityReset,.deleteAll: privateSession = true
    case .historySession: privateSession = false
    }
    return stop()
  }
  /// Native capability seam; does not implement a protected store or authentication.
  @discardableResult public func guardedPrivateEffect(_ token: GenerationToken, effect: PrivateEffect, action: () throws -> Void) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard accepts(token), !locked, !privateSession, ![.stopped,.setup,.error].contains(currentState), privateGate.allows(effect), accepts(token) else { return false }
    do { try action(); return accepts(token) }
    catch { stop(); currentState = .error; currentError = .unexpected; diagnostics.record(.memory,.unexpected,.error); return false }
  }
  @discardableResult public func releaseSpeech(_ token: GenerationToken, clause: String) -> Bool {
    lock.lock(); defer { lock.unlock() }
    guard !speakerRequired, accepts(token), [.thinking,.speaking].contains(currentState) else { return false }
    clearIdle()
    do { try effects.playClause(clause); guard accepts(token) else { return false }; currentState = .speaking; return true }
    catch { stop(); currentState = .error; currentError = .unexpected; diagnostics.record(.speech,.unexpected,.error); return false }
  }
  public func cancelGeneration() {
    lock.lock(); defer { lock.unlock() }
    guard !stopping else { return }
    guard permissionGranted() else { stop(); return }
    invalidateGeneration()
    do { try effects.cancelWork() } catch { stop(); currentState = .error; currentError = .unexpected; return }
    if [.capturing,.thinking,.speaking].contains(currentState) { currentState = .standby; issueGeneration(); updateIdle() }
  }
  @discardableResult public func stop() -> Bool {
    lock.lock(); defer { lock.unlock() }
    if stopping { return true }
    stopping=true; defer { stopping=false }
    startIntent=nil; capturePending=false; captureIntent=nil
    clearIdle(); hasConversation=false
    invalidateGeneration()
    currentState = .stopped; currentError = nil
    var failed = false
    let cleanups: [() throws -> Void] = [permission.cancelPendingRequests, effects.cancelWork, effects.releaseCapture, effects.clearVolatileContext]
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
    case .start: return [.stopped,.permissionRequired].contains(state) ? .standby : nil
    case .speechDetected: return state == .standby ? .capturing : nil
    case .endpoint: return state == .capturing ? .thinking : nil
    case .speechReady: return state == .thinking ? .speaking : nil
    case .playbackFinished: return state == .speaking ? .standby : nil
    case .pause: return [.standby, .capturing, .thinking, .speaking].contains(state) ? .paused : nil
    case .resume: return state == .paused ? .standby : nil
    }
  }
}

private final class CaptureCompletionResult {
  private let lock=NSLock(); private var value: Bool?
  func set(_ value: Bool) { lock.lock();defer { lock.unlock() };self.value=value }
  func get() -> Bool? { lock.lock();defer { lock.unlock() };return value }
}
