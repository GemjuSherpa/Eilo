import Foundation

public enum SafeError: String, Sendable { case permissionDenied, unavailable, timeout, quota, unexpected }
public enum SafeComponent: String, Sendable { case controller, capture, asr, model, speech, memory }
public enum SafeSeverity: String, Sendable { case info, warning, error }
public struct SafeDiagnostic: Equatable, Sendable {
  public let component: SafeComponent
  public let code: SafeError
  public let severity: SafeSeverity
}
/// No arbitrary string/Error/content inputs and no file/network/console sink.
public final class SafeDiagnostics: @unchecked Sendable {
  private let lock = NSLock()
  private var entries: [SafeDiagnostic] = []
  public init() {}
  public func record(_ component: SafeComponent, _ code: SafeError, _ severity: SafeSeverity) {
    lock.lock(); defer { lock.unlock() }
    if entries.count == 32 { entries.removeFirst() }
    entries.append(SafeDiagnostic(component: component, code: code, severity: severity))
  }
  public func snapshot() -> [SafeDiagnostic] {
    lock.lock(); defer { lock.unlock() }; return entries
  }
  public func clear() { lock.lock(); defer { lock.unlock() }; entries.removeAll() }
}
