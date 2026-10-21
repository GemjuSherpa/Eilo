package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
internal class ConsentStoreSpy(var saved:ConsentRecord?=null):ConsentPersistence {
 var succeeds=true
 override fun load()=saved
 override fun save(record:ConsentRecord):Boolean { if(succeeds) saved=record;return succeeds }
}
class ConsentPolicyTest {
 @Test fun legacyConsentMigratesWithoutEnablingMediaOrHistory() {
  val store=ConsentStoreSpy(ConsentRecord(version=1,historyChoice=HistoryChoice.PRIVATE,disclosureVersion=1,volume=70))
  val p=NativeConsentPolicy(store)
  assertTrue(p.canStart());assertEquals(70,p.snapshot()["volume"]);assertEquals(2,p.snapshot()["version"])
  assertEquals(mapOf("text" to true,"images" to false,"video" to false,"voiceOnly" to false),p.snapshot()["display"])
 }
 @Test fun displayChoicesSurviveRestartAndVoiceOnlyDoesNotEraseThem() {
  val store=ConsentStoreSpy();val p=NativeConsentPolicy(store)
  assertTrue(p.chooseDisplay("displayImages",true,true));assertTrue(p.chooseDisplay("displayText",false,true));assertTrue(p.chooseDisplay("voiceOnly",true,true))
  val restarted=NativeConsentPolicy(store)
  assertEquals(mapOf("text" to false,"images" to true,"video" to false,"voiceOnly" to true),restarted.snapshot()["display"])
  assertTrue(restarted.chooseDisplay("voiceOnly",false,true));assertEquals(mapOf("text" to false,"images" to true,"video" to false,"voiceOnly" to false),restarted.snapshot()["display"])
  assertFalse(restarted.canStart());assertFalse(restarted.personalWritesAllowed())
 }
 @Test fun lockedUnknownVoiceRouteAndFailedSavesCannotChangeDisplay() {
  val store=ConsentStoreSpy();val p=NativeConsentPolicy(store)
  assertFalse(p.chooseDisplay("displayVideo",true,false));assertFalse(p.chooseDisplay("voiceDisplay",true,true))
  store.succeeds=false;assertFalse(p.chooseDisplay("displayVideo",true,true))
  assertEquals(mapOf("text" to true,"images" to false,"video" to false,"voiceOnly" to false),p.snapshot()["display"])
 }
 @Test fun freshPermissionAndFailedSaveCannotEnableHistory() {
  val store=ConsentStoreSpy();val p=NativeConsentPolicy(store)
  assertEquals("none",p.snapshot()["historyChoice"]);assertFalse(p.completeOnboarding());assertFalse(p.canStart())
  val permission=FakePermission();permission.complete(MicrophonePermission.GRANTED)
  assertFalse(p.personalWritesAllowed());store.succeeds=false
  assertFalse(p.chooseHistory(HistoryChoice.HISTORY));assertEquals("none",p.snapshot()["historyChoice"])
 }
 @Test fun explicitChoiceIsVersionedAndDoesNotInventEncryptedStorage() {
  val store=ConsentStoreSpy();val p=NativeConsentPolicy(store)
  assertTrue(p.chooseHistory(HistoryChoice.HISTORY));assertTrue(p.completeOnboarding())
  assertEquals(2,store.saved!!.version);assertEquals("history",p.snapshot()["historyChoice"])
  assertFalse(p.personalWritesAllowed());assertFalse(p.canStart())
  assertTrue(p.chooseHistory(HistoryChoice.PRIVATE));assertTrue(p.canStart());assertFalse(p.personalWritesAllowed())
 }
 @Test fun backgroundRequiresItsOwnExplicitAuthenticatedChoice() {
  val store=ConsentStoreSpy();val p=NativeConsentPolicy(store)
  assertFalse(p.chooseBackground(true,true));p.chooseHistory(HistoryChoice.PRIVATE);p.completeOnboarding()
  assertFalse(p.chooseBackground(true,false));assertFalse(p.backgroundRequested())
  assertTrue(p.chooseBackground(true,true));assertTrue(p.backgroundRequested())
  assertTrue(p.chooseBackground(false,false));assertFalse(p.backgroundRequested())
 }
 @Test fun failedBackgroundSaveCannotEnableIt() {
  val store=ConsentStoreSpy();val p=NativeConsentPolicy(store);p.chooseHistory(HistoryChoice.PRIVATE);p.completeOnboarding()
  store.succeeds=false;assertFalse(p.chooseBackground(true,true));assertFalse(p.backgroundRequested())
 }
 @Test fun unsupportedConsentVersionResetsToNoChoice() {
  val p=NativeConsentPolicy(ConsentStoreSpy(ConsentRecord(version=3,historyChoice=HistoryChoice.HISTORY,disclosureVersion=1,backgroundConsent=true)))
  assertEquals("none",p.snapshot()["historyChoice"]);assertEquals(false,p.snapshot()["backgroundConsent"])
 }
}
