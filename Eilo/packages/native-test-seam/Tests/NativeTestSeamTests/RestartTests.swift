import XCTest
@testable import NativeTestSeam
final class RestartTests: XCTestCase {
  func testFreshProcessCannotRestoreListeningFromPriorControllerOrPermission() {
    let prior=testController(); prior.dispatch(.start); let old=prior.token!
    for _ in ["relaunch","reboot","restored installation"] {
      let spy=EffectsSpy(), permission=FakePermission(); let fresh=testController(effects:spy,permission:permission)
      XCTAssertEqual(fresh.state,.stopped); XCTAssertEqual(spy.started,0); XCTAssertEqual(permission.requests,0)
      XCTAssertFalse(fresh.releaseSpeech(old,clause:"old process")); XCTAssertNil(fresh.token)
    }
  }
  func testSnapshotOpaqueMetadataAndTypedErrors() {
    let c=testController(); let snapshot=c.snapshot()
    XCTAssertEqual(Set(snapshot.keys),Set(["version","state","sessionId","operationId","generation","privacyEpoch","modelStatus"]))
    XCTAssertEqual(snapshot["state"] as? String,"stopped"); XCTAssertNotNil(UUID(uuidString:snapshot["sessionId"] as! String))
    c.dispatch(.start); c.dispatch(.failure,failure:.timeout,token:c.token)
    XCTAssertEqual(c.snapshot()["errorCode"] as? String,"timeout")
  }
}
