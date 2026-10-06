import XCTest
@testable import NativeTestSeam
final class AudioInterruptionTests:XCTestCase {
 func testEachInterruptionClearsCaptureAndCannotResumeOldOutput() {
  for event in AudioInterruption.allCases {
   let spy=EffectsSpy(),c=testController(effects:spy)
   c.dispatch(.start);c.dispatch(.speechDetected,token:c.token);c.dispatch(.endpoint,token:c.token)
   let old=c.token!
   XCTAssertTrue(AudioInterruptionHandler(c).receive(event));XCTAssertTrue(old.cancelled)
   XCTAssertFalse(c.releaseSpeech(old,clause:"synthetic"));XCTAssertEqual(c.state,.stopped)
   XCTAssertEqual(spy.started,1);XCTAssertEqual(spy.released,1);XCTAssertTrue(spy.clauses.isEmpty)
  }
 }
}
