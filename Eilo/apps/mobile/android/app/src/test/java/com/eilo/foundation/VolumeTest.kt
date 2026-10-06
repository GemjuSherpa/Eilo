package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
private class GainSpy:ControllerEffects {
 var gain=1f;var captures=0
 override fun startCapture():Boolean { captures++;return true }
 override fun setOutputGain(gain:Float) { this.gain=gain }
 override fun playClause(clause:String) {};override fun cancelWork() {};override fun releaseCapture() {};override fun clearVolatileContext() {}
}
class VolumeTest {
 @Test fun gainChangeDoesNotChangeCaptureTokenOrConsent() {
  val e=GainSpy();val c=testController(effects=e);c.dispatch(ControllerEvent.START);val token=c.token()
  val p=NativeConsentPolicy(ConsentStoreSpy());val before=p.snapshot()
  assertTrue(c.setOutputGain(0.3f));assertEquals(0.3f,e.gain,0f);assertSame(token,c.token());assertEquals(1,e.captures)
  assertTrue(p.chooseVolume(30));assertEquals(before["historyChoice"],p.snapshot()["historyChoice"]);assertEquals(before["backgroundConsent"],p.snapshot()["backgroundConsent"])
 }
 @Test fun invalidGainAndFailedPersistenceCannotInventVolume() {
  val e=GainSpy();val c=testController(effects=e)
  assertFalse(c.setOutputGain(Float.NaN));assertFalse(c.setOutputGain(-1f));assertEquals(1f,e.gain,0f)
  val store=ConsentStoreSpy();store.succeeds=false;val p=NativeConsentPolicy(store)
  assertFalse(p.chooseVolume(120));assertFalse(p.chooseVolume(20));assertEquals(100,p.snapshot()["volume"])
 }
}
