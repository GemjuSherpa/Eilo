package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
internal class EffectsSpy : ControllerEffects {
    var onStart: (() -> Unit)? = null
    var started=0
    override fun startCapture(): Boolean { started++; onStart?.invoke(); return true }
    var cancelled = 0; var released = 0; var cleared = 0
    var context = byteArrayOf(1,2,3); val committedHistory = byteArrayOf(4,5)
    var onCancel: (() -> Unit)? = null
    var failCancellation = false
    var onPlay: (() -> Unit)? = null
    val clauses = mutableListOf<String>()
    override fun playClause(clause: String) { clauses.add(clause); onPlay?.invoke() }
    override fun cancelWork() { cancelled++; onCancel?.invoke(); if (failCancellation) throw IllegalStateException("SYNTHETIC_PRIVATE_MARKER") }
    override fun releaseCapture() { released++ }
    override fun clearVolatileContext() { cleared++; context.fill(0) }
}
class StopTransactionTest {
    @Test fun stopEveryReachableStateAndDropDelayedEvents() {
        val sequences = listOf(emptyList(),listOf(ControllerEvent.START),listOf(ControllerEvent.START,ControllerEvent.SPEECH_DETECTED),listOf(ControllerEvent.START,ControllerEvent.SPEECH_DETECTED,ControllerEvent.ENDPOINT),listOf(ControllerEvent.START,ControllerEvent.SPEECH_DETECTED,ControllerEvent.ENDPOINT,ControllerEvent.SPEECH_READY),listOf(ControllerEvent.START,ControllerEvent.PAUSE),listOf(ControllerEvent.FAILURE),listOf(ControllerEvent.SETUP_REQUIRED))
        for (events in sequences) {
            val spy = EffectsSpy(); val c=testController(effects=spy)
            events.forEach { c.dispatch(it,token=c.token()) }; spy.cancelled=0; spy.released=0; spy.cleared=0; assertTrue(c.stop())
            assertEquals(ControllerState.STOPPED,c.state())
            assertEquals(1,spy.cancelled); assertEquals(1,spy.released); assertEquals(1,spy.cleared)
            assertArrayEquals(byteArrayOf(0,0,0),spy.context); assertArrayEquals(byteArrayOf(4,5),spy.committedHistory)
            assertFalse(c.dispatch(ControllerEvent.SPEECH_READY)); assertFalse(c.dispatch(ControllerEvent.PLAYBACK_FINISHED))
        }
    }
    @Test fun cleanupCannotReentrantlyStartOrRecurseStop() {
        val spy=EffectsSpy(); val c=testController(effects=spy)
        spy.onCancel={ assertFalse(c.dispatch(ControllerEvent.START)); c.stop() }
        assertTrue(c.stop()); assertEquals(0,spy.started); assertEquals(1,spy.cancelled); assertNull(c.token()); assertEquals(ControllerState.STOPPED,c.state())
    }
    @Test fun cleanupFailureStillReleasesAndClearsWithoutLeakingCause() {
        val spy=EffectsSpy(); spy.failCancellation=true
        val diagnostics=SafeDiagnostics(); val c=testController(diagnostics,spy)
        assertFalse(c.stop()); assertEquals(1,spy.released); assertEquals(1,spy.cleared)
        assertEquals(ControllerState.ERROR,c.state()); assertEquals(SafeError.UNEXPECTED,c.error())
        assertFalse(diagnostics.snapshot().toString().contains("SYNTHETIC_PRIVATE_MARKER"))
    }
}
