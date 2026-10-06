package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class GenerationTest {
    private fun thinking(c: NativeController): GenerationToken {
        c.dispatch(ControllerEvent.START); c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token()); c.dispatch(ControllerEvent.ENDPOINT,token=c.token()); return c.token()!!
    }
    @Test fun oldAudioRejectedAfterCancelStopAndNewTurn() {
        val spy=EffectsSpy(); val c=NativeController(effects=spy); val old=thinking(c)
        c.cancelGeneration(); assertTrue(old.cancelled); assertFalse(c.releaseSpeech(old,"stale")); assertTrue(spy.clauses.isEmpty())
        c.dispatch(ControllerEvent.SPEECH_DETECTED) // no token: no new turn
        assertEquals(ControllerState.STANDBY,c.state())
        c.stop(); val fresh=thinking(c)
        assertFalse(c.releaseSpeech(old,"stale")); assertTrue(c.releaseSpeech(fresh,"synthetic approved clause"))
        c.stop(); assertFalse(c.releaseSpeech(fresh,"after Stop")); assertEquals(listOf("synthetic approved clause"),spy.clauses)
    }
    @Test fun reentrantStopCannotRestoreSpeaking() {
        val spy=EffectsSpy(); val c=NativeController(effects=spy); val token=thinking(c)
        spy.onPlay={ c.stop() }
        assertFalse(c.releaseSpeech(token,"synthetic")); assertEquals(ControllerState.STOPPED,c.state()); assertTrue(token.cancelled)
    }
    @Test fun tokenFromAnotherControllerAndUntokenedCompletionRejected() {
        val a=NativeController(); val b=NativeController(); val token=thinking(a); thinking(b)
        assertFalse(b.releaseSpeech(token,"wrong owner")); assertFalse(b.dispatch(ControllerEvent.SPEECH_READY)); assertEquals(ControllerState.THINKING,b.state())
    }
}
