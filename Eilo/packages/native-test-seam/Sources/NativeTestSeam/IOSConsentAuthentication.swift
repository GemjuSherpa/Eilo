#if os(iOS)
import LocalAuthentication
import Foundation
/// Called only for an explicit consent change, on the main queue; no app-account dependency.
public final class IOSConsentAuthentication {
 private var current:LAContext?
 public init() {}
 public func request(_ completion:@escaping (Bool)->Void) {
  guard current==nil else { completion(false);return }
  let context=LAContext();var error:NSError?
  guard context.canEvaluatePolicy(.deviceOwnerAuthentication,error:&error) else { completion(false);return }
  current=context
  context.evaluatePolicy(.deviceOwnerAuthentication,localizedReason:"Confirm your local Eilo consent choice") { [weak self] success,_ in
    DispatchQueue.main.async {
      guard let self else { completion(false);return }
      guard self.current === context else { completion(false);return }
      self.current=nil;completion(success)
    }
  }
 }
 public func cancel() { let previous=current;current=nil;previous?.invalidate() }
}
#endif
