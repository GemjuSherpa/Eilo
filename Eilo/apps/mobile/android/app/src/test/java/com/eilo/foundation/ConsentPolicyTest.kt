package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
internal class ConsentStoreSpy(var saved:ConsentRecord?=null):ConsentPersistence {
 var succeeds=true
 override fun load()=saved
 override fun save(record:ConsentRecord):Boolean { if(succeeds) saved=record;return succeeds }
}
class ConsentPolicyTest {
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
  assertEquals(1,store.saved!!.version);assertEquals("history",p.snapshot()["historyChoice"])
  assertFalse(p.personalWritesAllowed());assertFalse(p.canStart())
  assertTrue(p.chooseHistory(HistoryChoice.PRIVATE));assertTrue(p.canStart());assertFalse(p.personalWritesAllowed())
 }
 @Test fun unsupportedConsentVersionResetsToNoChoice() {
  val p=NativeConsentPolicy(ConsentStoreSpy(ConsentRecord(version=2,historyChoice=HistoryChoice.HISTORY,disclosureVersion=1,backgroundConsent=true)))
  assertEquals("none",p.snapshot()["historyChoice"]);assertEquals(false,p.snapshot()["backgroundConsent"])
 }
}
