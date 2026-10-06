import XCTest
@testable import NativeTestSeam
final class BackgroundCapturePolicyTests:XCTestCase {
 func testProductionBackgroundGateCannotBeOpenedByConsent() {
  XCTAssertFalse(BackgroundCapturePolicy.iosPhysicalPolicyVerified)
  XCTAssertFalse(BackgroundCapturePolicy.allows(visible:false,unlocked:true,permission:true,consent:true,capabilityVerified:BackgroundCapturePolicy.iosPhysicalPolicyVerified))
 }
 func testPermissionLockAndSeparateConsentMatrix() {
  for visible in [false,true] {
   XCTAssertFalse(BackgroundCapturePolicy.allows(visible:visible,unlocked:false,permission:true,consent:true,capabilityVerified:true))
   XCTAssertFalse(BackgroundCapturePolicy.allows(visible:visible,unlocked:true,permission:false,consent:true,capabilityVerified:true))
  }
  XCTAssertFalse(BackgroundCapturePolicy.allows(visible:false,unlocked:true,permission:true,consent:false,capabilityVerified:true))
  XCTAssertTrue(BackgroundCapturePolicy.allows(visible:true,unlocked:true,permission:true,consent:false,capabilityVerified:false))
 }
}
