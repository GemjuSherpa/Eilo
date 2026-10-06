import XCTest
@testable import NativeTestSeam
final class RouteGuardTests:XCTestCase {
 func testDisconnectCancelsAndExplicitUnlockedConfirmationIsRequired() {
  let e=EffectsSpy(),c=testController(effects:e);c.dispatch(.start);let old=c.token!
  c.routeDisconnected();XCTAssertTrue(old.cancelled);XCTAssertTrue(c.speakerConfirmationRequired)
  c.dispatch(.start);c.dispatch(.speechDetected,token:c.token);c.dispatch(.endpoint,token:c.token)
  XCTAssertFalse(c.releaseSpeech(c.token!,clause:"synthetic"));XCTAssertTrue(e.clauses.isEmpty)
  XCTAssertTrue(c.confirmSpeaker());XCTAssertTrue(c.releaseSpeech(c.token!,clause:"synthetic"))
  c.routeDisconnected();c.privacyTransition(.lock);XCTAssertFalse(c.confirmSpeaker());XCTAssertTrue(c.speakerConfirmationRequired)
 }
}
