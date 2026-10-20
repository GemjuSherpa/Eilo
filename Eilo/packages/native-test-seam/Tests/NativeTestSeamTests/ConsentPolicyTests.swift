import XCTest
@testable import NativeTestSeam
final class ConsentStoreSpy:ConsentPersistence {
 var saved:ConsentRecord?;var succeeds=true
 func load() throws -> ConsentRecord? { saved }
 func save(_ record:ConsentRecord) throws -> Bool { if succeeds { saved=record };return succeeds }
}
final class ConsentPolicyTests:XCTestCase {
 func testLegacyConsentMigratesWithoutChangingIndependentChoices() throws {
  let old=Data("{\"version\":1,\"historyChoice\":\"private\",\"disclosureVersion\":1,\"backgroundConsent\":false,\"volume\":70}".utf8)
  let store=ConsentStoreSpy();store.saved=try JSONDecoder().decode(ConsentRecord.self,from:old)
  let p=NativeConsentPolicy(persistence:store)
  XCTAssertTrue(p.canStart);XCTAssertEqual(p.snapshot()["volume"] as? Int,70)
  XCTAssertEqual(p.snapshot()["version"] as? Int,2)
  let display=p.snapshot()["display"] as? [String:Bool]
  XCTAssertEqual(display,["text":true,"images":false,"video":false,"voiceOnly":false])
 }
 func testDisplayChoicesPersistAcrossRestartAndVoiceOnlyDoesNotOverwriteThem() {
  let store=ConsentStoreSpy(),p=NativeConsentPolicy(persistence:store)
  XCTAssertTrue(p.chooseDisplay("displayImages",enabled:true,authorized:true))
  XCTAssertTrue(p.chooseDisplay("displayText",enabled:false,authorized:true))
  XCTAssertTrue(p.chooseDisplay("voiceOnly",enabled:true,authorized:true))
  let restarted=NativeConsentPolicy(persistence:store)
  XCTAssertEqual(restarted.snapshot()["display"] as? [String:Bool],["text":false,"images":true,"video":false,"voiceOnly":true])
  XCTAssertTrue(restarted.chooseDisplay("voiceOnly",enabled:false,authorized:true))
  XCTAssertEqual(restarted.snapshot()["display"] as? [String:Bool],["text":false,"images":true,"video":false,"voiceOnly":false])
  XCTAssertFalse(restarted.canStart);XCTAssertFalse(restarted.personalWritesAllowed)
 }
 func testDisplayRejectsLockedUnknownVoiceRoutesAndFailedPersistence() {
  let store=ConsentStoreSpy(),p=NativeConsentPolicy(persistence:store)
  XCTAssertFalse(p.chooseDisplay("displayVideo",enabled:true,authorized:false))
  XCTAssertFalse(p.chooseDisplay("voiceDisplay",enabled:true,authorized:true))
  store.succeeds=false;XCTAssertFalse(p.chooseDisplay("displayVideo",enabled:true,authorized:true))
  XCTAssertEqual(p.snapshot()["display"] as? [String:Bool],["text":true,"images":false,"video":false,"voiceOnly":false])
 }
 func testNoChoiceOrFailedSaveCannotEnableHistory() {
  let store=ConsentStoreSpy(),p=NativeConsentPolicy(persistence:store)
  XCTAssertEqual(p.snapshot()["historyChoice"] as? String,"none");XCTAssertFalse(p.completeOnboarding())
  store.succeeds=false;XCTAssertFalse(p.chooseHistory(.history));XCTAssertFalse(p.personalWritesAllowed)
 }
 func testExplicitIntentDoesNotInventProtectedHistoryCapability() {
  let store=ConsentStoreSpy(),p=NativeConsentPolicy(persistence:store)
  XCTAssertTrue(p.chooseHistory(.history));XCTAssertTrue(p.completeOnboarding());XCTAssertEqual(store.saved?.version,2)
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
  let store=ConsentStoreSpy();var record=ConsentRecord();record.version=3;record.historyChoice = .history;record.backgroundConsent=true;store.saved=record
  let p=NativeConsentPolicy(persistence:store);XCTAssertEqual(p.snapshot()["historyChoice"] as? String,"none");XCTAssertEqual(p.snapshot()["backgroundConsent"] as? Bool,false)
 }
}
