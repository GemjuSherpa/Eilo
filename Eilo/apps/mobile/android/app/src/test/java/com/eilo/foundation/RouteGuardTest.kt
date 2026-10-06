package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class RouteGuardTest {
 @Test fun disconnectedRouteCancelsOldOutputAndNewSpeechNeedsExplicitConfirmation() {
  val e=EffectsSpy();val c=testController(effects=e);c.dispatch(ControllerEvent.START);val old=c.token()!!
  c.routeDisconnected();assertTrue(old.cancelled);assertTrue(c.speakerConfirmationRequired());assertEquals(ControllerState.STOPPED,c.state())
  c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());c.dispatch(ControllerEvent.ENDPOINT,token=c.token())
  assertFalse(c.releaseSpeech(c.token()!!,"synthetic"));assertTrue(e.clauses.isEmpty())
  assertTrue(c.confirmSpeaker());assertTrue(c.releaseSpeech(c.token()!!,"synthetic"));assertEquals(1,e.clauses.size)
  c.routeDisconnected();c.privacyTransition(PrivacyChange.LOCK);assertFalse(c.confirmSpeaker());assertTrue(c.speakerConfirmationRequired())
 }
}
