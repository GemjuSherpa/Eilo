import XCTest
@testable import NativeTestSeam
final class EffectsSpy: ControllerEffects {
  var cancelled=0, released=0, cleared=0
  var context: [UInt8]=[1,2,3]; let committedHistory: [UInt8]=[4,5]
  var failCancellation=false
  var onPlay: (() -> Void)?
  var clauses: [String] = []
  func playClause(_ clause: String) throws { clauses.append(clause); onPlay?() }
  func cancelWork() throws { cancelled += 1; if failCancellation { throw NSError(domain:"SYNTHETIC_PRIVATE_MARKER",code:1) } }
  func releaseCapture() throws { released += 1 }
  func clearVolatileContext() throws { cleared += 1; context = [] }
}
final class StopTransactionTests: XCTestCase {
  func testStopEveryStateRejectsDelayedEvents() {
    let sequences: [[ControllerEvent]]=[[],[.start],[.start,.speechDetected],[.start,.speechDetected,.endpoint],[.start,.speechDetected,.endpoint,.speechReady],[.start,.pause],[.failure],[.setupRequired]]
    for events in sequences {
      let spy=EffectsSpy(); let c=NativeController(effects:spy)
      events.forEach { c.dispatch($0,token:c.token) }; spy.cancelled=0; spy.released=0; spy.cleared=0; XCTAssertTrue(c.stop())
      XCTAssertEqual(c.state,.stopped)
      XCTAssertEqual(spy.cancelled,1); XCTAssertEqual(spy.released,1); XCTAssertEqual(spy.cleared,1)
      XCTAssertTrue(spy.context.isEmpty); XCTAssertEqual(spy.committedHistory,[4,5])
      XCTAssertFalse(c.dispatch(.speechReady)); XCTAssertFalse(c.dispatch(.playbackFinished))
    }
  }
  func testFailureStillReleasesAndClearsWithoutCause() {
    let spy=EffectsSpy(); spy.failCancellation=true; let diagnostics=SafeDiagnostics()
    let c=NativeController(diagnostics:diagnostics,effects:spy)
    XCTAssertFalse(c.stop()); XCTAssertEqual(spy.released,1); XCTAssertEqual(spy.cleared,1)
    XCTAssertEqual(c.state,.error); XCTAssertEqual(c.error,.unexpected)
    XCTAssertFalse(String(describing:diagnostics.snapshot()).contains("SYNTHETIC_PRIVATE_MARKER"))
  }
}
