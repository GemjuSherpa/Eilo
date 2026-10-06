import XCTest
@testable import NativeTestSeam
struct AllowedPrivateGate: PrivateEffectGate { func allows(_ effect: PrivateEffect) -> Bool { true } }
final class PrivacyEpochTests: XCTestCase {
  func testTransitionsRejectStaleReadsWritesDisplayAndSpeech() {
    for change: PrivacyChange in [.lock,.unlock,.privateSession,.historySession,.identityReset,.deleteAll] {
      let spy=EffectsSpy(); let c=NativeController(effects:spy,privateGate:AllowedPrivateGate())
      c.privacyTransition(.historySession); c.dispatch(.start); c.dispatch(.speechDetected,token:c.token); c.dispatch(.endpoint,token:c.token); let old=c.token!
      var count=0; XCTAssertTrue(c.guardedPrivateEffect(old,effect:.readMemory) { count += 1 })
      c.privacyTransition(change)
      for effect: PrivateEffect in [.readMemory,.commitHistory,.displayPrivate] { XCTAssertFalse(c.guardedPrivateEffect(old,effect:effect) { count += 1 }) }
      XCTAssertFalse(c.releaseSpeech(old,clause:"stale private clause")); XCTAssertEqual(count,1); XCTAssertTrue(old.cancelled)
    }
  }
  func testDefaultPrivateAndLockNeverAuthorizeMemory() {
    let c=NativeController(); c.dispatch(.start)
    XCTAssertFalse(c.guardedPrivateEffect(c.token!,effect:.commitHistory) { XCTFail("unauthorized") })
    c.privacyTransition(.lock); XCTAssertFalse(c.dispatch(.start)); c.privacyTransition(.unlock)
    XCTAssertEqual(c.state,.stopped); XCTAssertNil(c.token)
  }
  func testDelayedThreadCannotCommitAfterLock() {
    let c=NativeController(privateGate:AllowedPrivateGate()); c.privacyTransition(.historySession); c.dispatch(.start); let old=c.token!
    let latch=DispatchSemaphore(value:0); let done=expectation(description:"delayed native callback")
    DispatchQueue.global().async { latch.wait(); XCTAssertFalse(c.guardedPrivateEffect(old,effect:.commitHistory) { XCTFail("stale commit") }); done.fulfill() }
    c.privacyTransition(.lock); latch.signal(); wait(for:[done],timeout:2)
  }
}
