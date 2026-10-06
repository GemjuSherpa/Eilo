import Foundation
public enum MicrophonePermission: CaseIterable { case notRequested, denied, granted, unavailable }
public protocol MicrophonePermissionAdapter {
  func status() -> MicrophonePermission
  func request(_ completion: @escaping (MicrophonePermission) -> Void)
  func cancelPendingRequests()
}
public extension MicrophonePermissionAdapter { func cancelPendingRequests() {} }
public struct UnavailablePermissionAdapter: MicrophonePermissionAdapter {
  public init() {}
  public func status() -> MicrophonePermission { .unavailable }
  public func request(_ completion: @escaping (MicrophonePermission) -> Void) { completion(.unavailable) }
}
#if os(iOS)
import AVFAudio
/// OS permission only. No AVAudioSession activation, tap, capture or background mode.
public final class IOSMicrophonePermission: MicrophonePermissionAdapter, @unchecked Sendable {
  private let lock=NSLock()
  private var revision=UUID()
  public init() {}
  public func cancelPendingRequests() { lock.lock(); defer { lock.unlock() }; revision=UUID() }
  public func status() -> MicrophonePermission {
    if #available(iOS 17.0, *) {
      switch AVAudioApplication.shared.recordPermission {
      case .undetermined: return .notRequested
      case .denied: return .denied
      case .granted: return .granted
      @unknown default: return .unavailable
      }
    } else {
      switch AVAudioSession.sharedInstance().recordPermission {
      case .undetermined: return .notRequested
      case .denied: return .denied
      case .granted: return .granted
      @unknown default: return .unavailable
      }
    }
  }
  public func request(_ completion: @escaping (MicrophonePermission) -> Void) {
    lock.lock(); let expected=revision; lock.unlock()
    DispatchQueue.main.async { [weak self] in
      guard let self else { return }
      self.lock.lock(); let valid=self.revision == expected; self.lock.unlock()
      guard valid else { return }
      let before=self.status()
      guard before == .notRequested else { completion(before); return }
      if #available(iOS 17.0, *) { AVAudioApplication.requestRecordPermission { _ in completion(self.status()) } }
      else { AVAudioSession.sharedInstance().requestRecordPermission { _ in completion(self.status()) } }
    }
  }
}
#endif
