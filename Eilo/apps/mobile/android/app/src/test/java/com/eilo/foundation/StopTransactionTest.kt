package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
internal class EffectsSpy : ControllerEffects {
    var cancelled = 0; var released = 0; var cleared = 0
    var context = byteArrayOf(1,2,3); val committedHistory = byteArrayOf(4,5)
    var failCancellation = false
    override fun cancelWork() { cancelled++; if (failCancellation) throw IllegalStateException("SYNTHETIC_PRIVATE_MARKER") }
    override fun releaseCapture() { released++ }
    override fun clearVolatileContext() { cleared++; context.fill(0) }
}
class StopTransactionTest {
    @Test fun stopEveryReachableStateAndDropDelayedEvents() {
        val sequences = listOf(emptyList(),listOf(ControllerEvent.START),listOf(ControllerEvent.START,ControllerEvent.SPEECH_DETECTED),listOf(ControllerEvent.START,ControllerEvent.SPEECH_DETECTED,ControllerEvent.ENDPOINT),listOf(ControllerEvent.START,ControllerEvent.SPEECH_DETECTED,ControllerEvent.ENDPOINT,ControllerEvent.SPEECH_READY),listOf(ControllerEvent.START,ControllerEvent.PAUSE),listOf(ControllerEvent.FAILURE),listOf(ControllerEvent.SETUP_REQUIRED))
        for (events in sequences) {
            val spy = EffectsSpy(); val c=NativeController(effects=spy)
            events.forEach { c.dispatch(it) }; assertTrue(c.stop())
            assertEquals(ControllerState.STOPPED,c.state())
            assertEquals(1,spy.cancelled); assertEquals(1,spy.released); assertEquals(1,spy.cleared)
            assertArrayEquals(byteArrayOf(0,0,0),spy.context); assertArrayEquals(byteArrayOf(4,5),spy.committedHistory)
            assertFalse(c.dispatch(ControllerEvent.SPEECH_READY)); assertFalse(c.dispatch(ControllerEvent.PLAYBACK_FINISHED))
        }
    }
    @Test fun cleanupFailureStillReleasesAndClearsWithoutLeakingCause() {
        val spy=EffectsSpy(); spy.failCancellation=true
        val diagnostics=SafeDiagnostics(); val c=NativeController(diagnostics,spy)
        assertFalse(c.stop()); assertEquals(1,spy.released); assertEquals(1,spy.cleared)
        assertEquals(ControllerState.ERROR,c.state()); assertEquals(SafeError.UNEXPECTED,c.error())
        assertFalse(diagnostics.snapshot().toString().contains("SYNTHETIC_PRIVATE_MARKER"))
    }
}
