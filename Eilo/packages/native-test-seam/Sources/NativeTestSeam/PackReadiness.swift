import Foundation
public enum ModelStatus: String, CaseIterable, Sendable { case ready,missing,incompatible,corrupt,incomplete,unsupported,offlineVoiceMissing="offline_voice_missing" }
public protocol ModelReadinessAdapter { func status() -> ModelStatus }
public struct MissingModelReadiness: ModelReadinessAdapter { public init() {};public func status() -> ModelStatus { .missing } }
/// Installer-worker refresh; constant-time native status without model disk/network IO on controller/audio threads.
public final class PackReadiness: ModelReadinessAdapter {
  private let store: PackStore,lock=NSLock()
  private var value: ModelStatus = .missing,epoch: UUID?
  private var refreshID=UUID()
  public init(store: PackStore) { self.store=store }
  public func status() -> ModelStatus { lock.lock();defer { lock.unlock() };return epoch==store.epoch ? value:.missing }
  public func invalidate() { lock.lock();refreshID=UUID();epoch=nil;value = .missing;lock.unlock() }
  @discardableResult public func refresh(configurationSupported: Bool=false,offlineVoice: Bool=false) -> ModelStatus {
    lock.lock();let request=UUID();refreshID=request;lock.unlock()
    let before=store.epoch
    let result: ModelStatus
    if !configurationSupported { result = .unsupported }
    else {
      do {
        if let p=try store.active() {
          if !Set(p.manifest.artifacts.map(\.role)).isSuperset(of:["llm","asr","wake","vad"]) { result = .incomplete }
          else { result = offlineVoice ? .ready:.offlineVoiceMissing }
        } else { result = .missing }
      } catch PackFailure.incompatible { result = .incompatible } catch { result = .corrupt }
    }
    lock.lock();if refreshID==request { value=result;epoch=before };lock.unlock();return status()
  }
}
