import XCTest
@testable import NativeTestSeam
final class ConsentStoreSpy:ConsentPersistence {
 var saved:ConsentRecord?;var succeeds=true
 func load() throws -> ConsentRecord? { saved }
 func save(_ record:ConsentRecord) throws -> Bool { if succeeds { saved=record };return succeeds }
}
final class ConsentPolicyTests:XCTestCase {
 func testNoChoiceOrFailedSaveCannotEnableHistory() {
  let store=ConsentStoreSpy(),p=NativeConsentPolicy(persistence:store)
  XCTAssertEqual(p.snapshot()["historyChoice"] as? String,"none");XCTAssertFalse(p.completeOnboarding())
  store.succeeds=false;XCTAssertFalse(p.chooseHistory(.history));XCTAssertFalse(p.personalWritesAllowed)
 }
 func testExplicitIntentDoesNotInventProtectedHistoryCapability() {
  let store=ConsentStoreSpy(),p=NativeConsentPolicy(persistence:store)
  XCTAssertTrue(p.chooseHistory(.history));XCTAssertTrue(p.completeOnboarding());XCTAssertEqual(store.saved?.version,1)
  XCTAssertFalse(p.personalWritesAllowed);XCTAssertFalse(p.canStart)
  XCTAssertTrue(p.chooseHistory(.privateMode));XCTAssertTrue(p.canStart);XCTAssertFalse(p.personalWritesAllowed)
 }
 func testBackgroundNeedsIndependentAuthenticatedChoice() {
  let store=ConsentStoreSpy(),p=NativeConsentPolicy(persistence:store)
  XCTAssertFalse(p.chooseBackground(true,authenticated:true));p.chooseHistory(.privateMode);p.completeOnboarding()
  XCTAssertFalse(p.chooseBackground(true,authenticated:false));XCTAssertFalse(p.backgroundRequested)
  XCTAssertTrue(p.chooseBackground(true,authenticated:true));XCTAssertTrue(p.backgroundRequested)
  XCTAssertTrue(p.chooseBackground(false,authenticated:false));XCTAssertFalse(p.backgroundRequested)
 }
 func testFailedBackgroundPersistenceDoesNotEnable() {
  let store=ConsentStoreSpy(),p=NativeConsentPolicy(persistence:store);p.chooseHistory(.privateMode);p.completeOnboarding();store.succeeds=false
  XCTAssertFalse(p.chooseBackground(true,authenticated:true));XCTAssertFalse(p.backgroundRequested)
 }
 func testUnknownVersionDefaultsToUnselectedAndBackgroundOff() {
  let store=ConsentStoreSpy();var record=ConsentRecord();record.version=2;record.historyChoice = .history;record.backgroundConsent=true;store.saved=record
  let p=NativeConsentPolicy(persistence:store);XCTAssertEqual(p.snapshot()["historyChoice"] as? String,"none");XCTAssertEqual(p.snapshot()["backgroundConsent"] as? Bool,false)
 }
}
