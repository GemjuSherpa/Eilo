import Foundation
/// Production iOS background capability remains closed until physical lock-policy evidence exists.
public enum BackgroundCapturePolicy {
 public static let iosPhysicalPolicyVerified=false
 public static func allows(visible:Bool,unlocked:Bool,permission:Bool,consent:Bool,capabilityVerified:Bool)->Bool {
  unlocked && permission && (visible || (consent && capabilityVerified))
 }
}
