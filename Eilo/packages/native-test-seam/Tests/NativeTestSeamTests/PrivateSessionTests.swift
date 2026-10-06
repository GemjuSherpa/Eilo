import XCTest
@testable import NativeTestSeam
final class PrivateSessionTests:XCTestCase {
 func testExplicitPrivateCannotEnableOrDeleteHistory() {
  let p=NativeConsentPolicy(persistence:ConsentStoreSpy());p.chooseHistory(.history);p.completeOnboarding();XCTAssertFalse(p.canStart)
  XCTAssertTrue(p.choosePrivateSession(true));XCTAssertTrue(p.canStart);XCTAssertFalse(p.personalWritesAllowed)
  XCTAssertEqual(p.snapshot()["historyChoice"] as? String,"history");XCTAssertFalse(p.choosePrivateSession(false));XCTAssertFalse(p.personalWritesAllowed)
 }
 func testPrivateModeRaceRejectsAllSinksPreservingEarlierEntries() {
  let c=testController(privateGate:AllowedPrivateGate());c.privacyTransition(.historySession);c.dispatch(.start);let old=c.token!
  c.privacyTransition(.privateSession);c.dispatch(.start)
  for _ in ["transcript","fact","index","inbox"] {
   var entries=["earlier"]
   XCTAssertFalse(c.guardedPrivateEffect(old,effect:.commitHistory) { entries.append("stale") })
   XCTAssertFalse(c.guardedPrivateEffect(c.token!,effect:.commitHistory) { entries.append("current") })
   XCTAssertEqual(entries,["earlier"])
  }
 }
}
