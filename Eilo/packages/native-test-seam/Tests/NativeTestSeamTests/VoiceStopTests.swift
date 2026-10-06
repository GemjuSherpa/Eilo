import XCTest
@testable import NativeTestSeam
final class VoiceStopTests: XCTestCase {
  func testRecognizedStopNeedsNoModelAndUsesSameCleanup() {
    let spy=EffectsSpy(); spy.failCancellation=true; let c=testController(effects:spy)
    c.dispatch(.start); let old=c.token!
    XCTAssertFalse(c.recognizedCommand(" Stop Listening ",token:old))
    XCTAssertEqual(spy.released,1); XCTAssertEqual(spy.cleared,1); XCTAssertTrue(old.cancelled); XCTAssertTrue(spy.clauses.isEmpty)
  }
  func testExactCommandsAndStaleRecognition() {
    let spy=EffectsSpy(); let c=testController(effects:spy); c.dispatch(.start); let old=c.token!
    XCTAssertFalse(c.recognizedCommand("please stop",token:old)); XCTAssertTrue(c.recognizedCommand("end conversation",token:old)); XCTAssertEqual(spy.released,0)
    XCTAssertFalse(c.recognizedCommand("stop listening",token:old)); XCTAssertTrue(c.recognizedCommand("stop listening",token:c.token!)); XCTAssertEqual(c.state,.stopped); XCTAssertEqual(spy.released,1)
  }
}
