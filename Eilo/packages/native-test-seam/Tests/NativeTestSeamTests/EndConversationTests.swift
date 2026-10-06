import XCTest
@testable import NativeTestSeam
final class EndConversationTests: XCTestCase {
  func testEndPreservesCaptureButStopReleasesIt() {
    for length in 1...4 {
      let spy=EffectsSpy(); let c=testController(effects:spy)
      let events: [ControllerEvent]=[.start,.speechDetected,.endpoint,.speechReady]
      events.prefix(length).forEach { c.dispatch($0,token:c.token) }; let old=c.token!
      XCTAssertTrue(c.endConversation()); XCTAssertEqual(c.state,.standby); XCTAssertTrue(old.cancelled)
      XCTAssertEqual(spy.released,0); XCTAssertEqual(spy.cleared,1); XCTAssertFalse(c.releaseSpeech(old,clause:"stale"))
      c.stop(); XCTAssertEqual(spy.released,1); XCTAssertFalse(c.endConversation()); XCTAssertEqual(c.state,.stopped)
    }
  }
}
