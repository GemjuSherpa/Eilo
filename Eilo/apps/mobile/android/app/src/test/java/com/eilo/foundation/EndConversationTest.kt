package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class EndConversationTest {
    @Test fun endPreservesCaptureButStopReleasesIt() {
        for (length in 1..4) {
            val spy=EffectsSpy(); val c=NativeController(effects=spy)
            listOf(ControllerEvent.START,ControllerEvent.SPEECH_DETECTED,ControllerEvent.ENDPOINT,ControllerEvent.SPEECH_READY).take(length).forEach { c.dispatch(it,token=c.token()) }
            val old=c.token()!!
            assertTrue(c.endConversation()); assertEquals(ControllerState.STANDBY,c.state()); assertTrue(old.cancelled)
            assertEquals(0,spy.released); assertEquals(1,spy.cleared); assertFalse(c.releaseSpeech(old,"stale"))
            c.stop(); assertEquals(1,spy.released); assertFalse(c.endConversation()); assertEquals(ControllerState.STOPPED,c.state())
        }
    }
}
