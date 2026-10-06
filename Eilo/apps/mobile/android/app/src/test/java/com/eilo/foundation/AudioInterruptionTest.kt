package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class AudioInterruptionTest {
 @Test fun everyInterruptionStopsAndRejectsLateOutputWithoutRestart() {
  for (event in AudioInterruption.entries) {
   val spy=EffectsSpy();val c=testController(effects=spy);c.dispatch(ControllerEvent.START)
   c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());c.dispatch(ControllerEvent.ENDPOINT,token=c.token())
   val old=c.token()!!
   assertTrue(AudioInterruptionHandler(c).receive(event));assertTrue(old.cancelled)
   assertFalse(c.releaseSpeech(old,"synthetic"));assertEquals(ControllerState.STOPPED,c.state())
   assertEquals(1,spy.started);assertEquals(1,spy.released);assertTrue(spy.clauses.isEmpty())
  }
 }
}
