import XCTest
@testable import NativeTestSeam
final class GenerationTests: XCTestCase {
  func thinking(_ c: NativeController) -> GenerationToken {
    c.dispatch(.start); c.dispatch(.speechDetected,token:c.token); c.dispatch(.endpoint,token:c.token); return c.token!
  }
  func testOldAudioAfterCancelStopAndNewTurn() {
    let spy=EffectsSpy(); let c=NativeController(effects:spy); let old=thinking(c)
    c.cancelGeneration(); XCTAssertTrue(old.cancelled); XCTAssertFalse(c.releaseSpeech(old,clause:"stale")); XCTAssertTrue(spy.clauses.isEmpty)
    c.dispatch(.speechDetected); XCTAssertEqual(c.state,.standby)
    c.stop(); let fresh=thinking(c)
    XCTAssertFalse(c.releaseSpeech(old,clause:"stale")); XCTAssertTrue(c.releaseSpeech(fresh,clause:"synthetic approved clause"))
    c.stop(); XCTAssertFalse(c.releaseSpeech(fresh,clause:"after Stop")); XCTAssertEqual(spy.clauses,["synthetic approved clause"])
  }
  func testReentrantStopCannotRestoreSpeaking() {
    let spy=EffectsSpy(); let c=NativeController(effects:spy); let token=thinking(c)
    spy.onPlay={ c.stop() }
    XCTAssertFalse(c.releaseSpeech(token,clause:"synthetic")); XCTAssertEqual(c.state,.stopped); XCTAssertTrue(token.cancelled)
  }
  func testWrongOwnerAndUntokenedCompletionRejected() {
    let a=NativeController(), b=NativeController(); let token=thinking(a); _=thinking(b)
    XCTAssertFalse(b.releaseSpeech(token,clause:"wrong owner")); XCTAssertFalse(b.dispatch(.speechReady)); XCTAssertEqual(b.state,.thinking)
  }
}
