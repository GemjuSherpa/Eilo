import XCTest
@testable import NativeTestSeam
private final class GainSpy:ControllerEffects {
 var gain:Float=1;var captures=0
 func startCapture() throws -> Bool { captures += 1;return true }
 func setOutputGain(_ gain:Float) throws { self.gain=gain }
 func playClause(_ clause:String) throws {};func cancelWork() throws {};func releaseCapture() throws {};func clearVolatileContext() throws {}
}
final class VolumeTests:XCTestCase {
 func testGainDoesNotAlterCaptureOrConsent() {
  let e=GainSpy(),c=testController(effects:e);c.dispatch(.start);let token=c.token
  let p=NativeConsentPolicy(persistence:ConsentStoreSpy()),before=p.snapshot()
  XCTAssertTrue(c.setOutputGain(0.3));XCTAssertEqual(e.gain,0.3);XCTAssertTrue(c.token === token);XCTAssertEqual(e.captures,1)
  XCTAssertTrue(p.chooseVolume(30));XCTAssertEqual(p.snapshot()["historyChoice"] as? String,before["historyChoice"] as? String);XCTAssertEqual(p.snapshot()["backgroundConsent"] as? Bool,false)
 }
 func testInvalidGainAndFailedSaveAreRejected() {
  let e=GainSpy(),c=testController(effects:e);XCTAssertFalse(c.setOutputGain(.nan));XCTAssertFalse(c.setOutputGain(-1));XCTAssertEqual(e.gain,1)
  let store=ConsentStoreSpy();store.succeeds=false;let p=NativeConsentPolicy(persistence:store)
  XCTAssertFalse(p.chooseVolume(120));XCTAssertFalse(p.chooseVolume(20));XCTAssertEqual(p.snapshot()["volume"] as? Int,100)
 }
}
