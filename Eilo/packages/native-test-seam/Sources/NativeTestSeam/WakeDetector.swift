import Foundation

/// Keyword-only native backend. Consume borrowed samples synchronously; no ASR text or PCM bridge.
protocol WakeKeywordStream: AnyObject {
  func accept(_ samples: UnsafeBufferPointer<Float>, sampleRate: Int) throws
  func ready() throws -> Bool
  func decode() throws
  func keyword() throws -> String
  func reset() throws
  func close() throws
}
struct WakeConfiguration {
  let phrase: String
  let threshold: Float
  let boost: Float
  init(phrase: String, threshold: Float, boost: Float) throws {
    guard phrase.utf8.count <= 64, phrase.range(of:"^[A-Z]+( [A-Z]+){0,7}$",options:.regularExpression) != nil,
      threshold.isFinite, threshold > 0, threshold <= 1, boost.isFinite, boost > 0, boost <= 10 else { throw WakeFailure.unavailable }
    self.phrase=phrase;self.threshold=threshold;self.boost=boost
  }
}
final class WakeLease {
  private let lock=NSLock();private var valid=true
  var active:Bool { lock.lock();defer { lock.unlock() };return valid }
  func revoke() { lock.lock();valid=false;lock.unlock() }
}
struct WakeActivation {
  private let token: GenerationToken
  private let lease:WakeLease
  fileprivate init(_ token: GenerationToken, _ lease:WakeLease) { self.token=token;self.lease=lease }
  func apply(_ controller: NativeController) -> Bool { controller.wakeDetected(token,active:{lease.active}) }
}
enum WakeFailure: Error { case unavailable }

/// Serialized native worker only. An independently verified backend is required; defaults fail closed.
/// Fixed scratch holds at most 100 ms at 192 kHz; it is erased before returning to the caller.
final class WakeDetector {
  private let lock=NSRecursiveLock()
  private let configuration: WakeConfiguration
  private let verified: () -> Bool
  private let open: (WakeConfiguration) throws -> any WakeKeywordStream
  private let scratch=UnsafeMutableBufferPointer<Float>.allocate(capacity:19200)
  private let diagnostics: SafeDiagnostics
  private var releaseFailed=false
  private var stream: (any WakeKeywordStream)?
  private var token: GenerationToken?
  private var lease:WakeLease?
  init(configuration: WakeConfiguration, diagnostics: SafeDiagnostics = SafeDiagnostics(), verified: @escaping () -> Bool = { false }, open: @escaping (WakeConfiguration) throws -> any WakeKeywordStream = { _ in throw WakeFailure.unavailable }) {
    self.configuration=configuration;self.verified=verified;self.open=open;self.diagnostics=diagnostics
    scratch.initialize(repeating:0)
  }
  func begin(_ expected: GenerationToken) -> Bool {
    lock.lock();defer { lock.unlock() };close()
    guard !expected.cancelled, !releaseFailed, verified() else { return false }
    do {
      stream=try open(configuration)
      guard !expected.cancelled, !releaseFailed, verified() else { close();return false }
      token=expected;lease=WakeLease();return true
    } catch { close();return false }
  }
  func process(_ expected: GenerationToken, input: UnsafeBufferPointer<Float>, sampleRate: Int) -> WakeActivation? {
    lock.lock();defer { lock.unlock() }
    guard expected === token, !expected.cancelled else { if expected === token { close() };return nil }
    guard (8000...192000).contains(sampleRate), !input.isEmpty, input.count <= sampleRate/10, input.allSatisfy({ $0.isFinite && (-1...1).contains($0) }), let engine=stream, let currentLease=lease else { close();return nil }
    defer { erase() }
    do {
      guard verified() else { close();return nil }
      for i in input.indices { scratch[i]=input[i] }
      try engine.accept(UnsafeBufferPointer(start:scratch.baseAddress,count:input.count),sampleRate:sampleRate)
      var steps=0
      while try engine.ready() { steps += 1;guard steps <= 32 else { throw WakeFailure.unavailable };try engine.decode() }
      let keyword=try engine.keyword()
      let activation=keyword==configuration.phrase
      if !keyword.isEmpty { try engine.reset() }
      guard !expected.cancelled, verified() else { close();return nil }
      return activation && expected === token && currentLease === lease ? WakeActivation(expected,currentLease) : nil
    } catch { diagnostics.record(.model,.unavailable,.error);close();return nil }
  }
  private func erase() { scratch.update(repeating:0) }
  deinit { close();scratch.deinitialize();scratch.deallocate() }
  func close() {
    lock.lock();defer { lock.unlock() };lease?.revoke();lease=nil;let previous=stream;stream=nil;token=nil;erase()
    // Close to all future input even when native release reports a failure.
    do { try previous?.close() } catch { releaseFailed=true;diagnostics.record(.model,.unavailable,.error) }
  }
}
