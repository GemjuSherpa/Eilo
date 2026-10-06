import XCTest
@testable import NativeTestSeam
final class NativeControllerTests: XCTestCase {
  func testDeclaredEdgesAndInvalidEvents() {
    let edges: [ControllerEvent: Set<ControllerState>] = [
      .setupRequired:[.stopped], .ready:[.setup,.error], .start:[.stopped,.permissionRequired],
      .speechDetected:[.standby], .endpoint:[.capturing], .speechReady:[.thinking],
      .playbackFinished:[.speaking], .pause:[.standby,.capturing,.thinking,.speaking],
      .resume:[.paused], .stop:Set(ControllerState.allCases), .failure:Set(ControllerState.allCases)]
    for state in ControllerState.allCases { for event in ControllerEvent.allCases {
      XCTAssertEqual(edges[event]!.contains(state), NativeController.nextState(state,event) != nil)
    }}
  }
  func testSyntheticTurnAndTypedFailure() {
    let c = testController()
    XCTAssertFalse(c.dispatch(.speechReady)); XCTAssertEqual(c.state,.stopped)
    for e: ControllerEvent in [.start,.speechDetected,.endpoint,.speechReady,.playbackFinished] { XCTAssertTrue(c.dispatch(e,token:c.token)) }
    XCTAssertEqual(c.state,.standby)
    c.dispatch(.failure,failure:.timeout,token:c.token); XCTAssertEqual(c.error,.timeout)
    c.dispatch(.ready); XCTAssertNil(c.error)
  }
}
