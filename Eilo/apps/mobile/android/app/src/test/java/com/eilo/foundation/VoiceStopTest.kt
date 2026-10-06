package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class VoiceStopTest {
    @Test fun recognizedStopNeedsNoModelAndUsesSameCleanup() {
        val spy=EffectsSpy(); spy.failCancellation=true; val c=NativeController(effects=spy)
        c.dispatch(ControllerEvent.START); val old=c.token()!!
        assertFalse(c.recognizedCommand(" Stop Listening ",old)) // cleanup failure is reported, release still attempted
        assertEquals(1,spy.released); assertEquals(1,spy.cleared); assertTrue(old.cancelled); assertTrue(spy.clauses.isEmpty())
    }
    @Test fun exactCommandsAndStaleRecognition() {
        val spy=EffectsSpy(); val c=NativeController(effects=spy); c.dispatch(ControllerEvent.START); val old=c.token()!!
        assertFalse(c.recognizedCommand("please stop",old)); assertTrue(c.recognizedCommand("end conversation",old)); assertEquals(0,spy.released)
        assertFalse(c.recognizedCommand("stop listening",old)); assertTrue(c.recognizedCommand("stop listening",c.token()!!)); assertEquals(ControllerState.STOPPED,c.state()); assertEquals(1,spy.released)
    }
}
