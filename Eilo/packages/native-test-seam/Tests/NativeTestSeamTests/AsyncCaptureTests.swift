import XCTest
@testable import NativeTestSeam
private final class DeferredCapture: ControllerEffects {
  var completions=[(Bool)->Void]();var failures=[()->Void]();var releases=0
  func startCapture() throws -> Bool { false }
  func beginCapture(completion: @escaping (Bool)->Void,failure: @escaping ()->Void) throws { completions.append(completion);failures.append(failure) }
  func releaseCapture() throws { releases += 1 }
  func cancelWork() throws {};func clearVolatileContext() throws {};func playClause(_ clause:String) throws {}
}
final class AsyncCaptureTests:XCTestCase {
  func testPendingIsNotListeningAndCannotDuplicate() {
    let effects=DeferredCapture(),c=testController(effects:DeferredCapture())
    XCTAssertEqual(c.state,.stopped)
    let active=testController(effects:effects)
    XCTAssertTrue(active.dispatch(.start));XCTAssertNil(active.token);XCTAssertFalse(active.dispatch(.start))
    effects.completions[0](true);XCTAssertEqual(active.state,.standby);XCTAssertNotNil(active.token)
  }
  func testStopAndOldFailureCannotAffectNewRun() {
    let effects=DeferredCapture(),c=testController(effects:effects)
    c.dispatch(.start);c.stop();effects.completions[0](true);XCTAssertNil(c.token)
    c.dispatch(.start);effects.completions[1](true);effects.failures[0]();XCTAssertEqual(c.state,.standby)
    let token=c.token!;effects.failures[1]();XCTAssertTrue(token.cancelled);XCTAssertEqual(c.state,.error)
  }
  func testRevocationOrSetupWhileOpeningFailsClosed() {
    for setup in [true,false] {
      let effects=DeferredCapture(),permission=FakePermission(),c=testController(effects:effects,permission:permission)
      c.dispatch(.start)
      if setup { c.dispatch(.setupRequired) } else { permission.value = .denied }
      effects.completions[0](true);XCTAssertNil(c.token);XCTAssertEqual(c.state,.stopped)
    }
  }
}
