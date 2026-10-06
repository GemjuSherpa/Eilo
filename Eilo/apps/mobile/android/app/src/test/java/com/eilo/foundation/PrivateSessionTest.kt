package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class PrivateSessionTest {
 @Test fun explicitPrivateAllowsUnsavedUseWithoutEnablingHistory() {
  val store=ConsentStoreSpy();val p=NativeConsentPolicy(store)
  p.chooseHistory(HistoryChoice.HISTORY);p.completeOnboarding();assertFalse(p.canStart())
  val before=p.snapshot();assertTrue(p.choosePrivateSession(true));assertTrue(p.canStart());assertFalse(p.personalWritesAllowed())
  assertEquals(before["historyChoice"],p.snapshot()["historyChoice"]);assertFalse(p.choosePrivateSession(false));assertFalse(p.personalWritesAllowed())
 }
 @Test fun privateModeRaceBlocksEveryPersonalSinkAndPreservesEarlierEntries() {
  val p=NativeConsentPolicy(ConsentStoreSpy());p.chooseHistory(HistoryChoice.HISTORY);p.completeOnboarding()
  val c=testController(privateGate=PrivateEffectGate { p.personalWritesAllowed() });c.privacyTransition(PrivacyChange.HISTORY_SESSION);c.dispatch(ControllerEvent.START);val old=c.token()!!
  val sinks=mapOf("transcript" to mutableListOf("earlier"),"fact" to mutableListOf("earlier"),"index" to mutableListOf("earlier"),"inbox" to mutableListOf("earlier"))
  c.privacyTransition(PrivacyChange.PRIVATE_SESSION);p.choosePrivateSession(true);c.dispatch(ControllerEvent.START)
  for(entries in sinks.values) {
   assertFalse(c.guardedPrivateEffect(old,PrivateEffect.COMMIT_HISTORY) { entries.add("stale") })
   assertFalse(c.guardedPrivateEffect(c.token()!!,PrivateEffect.COMMIT_HISTORY) { entries.add("current") })
   assertEquals(listOf("earlier"),entries)
  }
 }
}
