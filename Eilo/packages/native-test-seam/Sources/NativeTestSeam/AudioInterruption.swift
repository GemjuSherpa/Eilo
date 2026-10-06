import Foundation
public enum AudioInterruption: CaseIterable { case call,focusLoss,permissionLoss,captureContention,engineReset }
public final class AudioInterruptionHandler {
  private let controller: NativeController
  public init(_ controller: NativeController) { self.controller=controller }
  @discardableResult public func receive(_ event:AudioInterruption) -> Bool { controller.stop() }
}
