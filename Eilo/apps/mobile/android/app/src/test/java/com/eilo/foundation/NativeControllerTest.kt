package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class NativeControllerTest {
    @Test fun transitionsFollowOnlyDeclaredEdges() {
        val edges = mapOf(
            ControllerEvent.SETUP_REQUIRED to setOf(ControllerState.STOPPED),
            ControllerEvent.READY to setOf(ControllerState.SETUP, ControllerState.ERROR),
            ControllerEvent.START to setOf(ControllerState.STOPPED),
            ControllerEvent.SPEECH_DETECTED to setOf(ControllerState.STANDBY),
            ControllerEvent.ENDPOINT to setOf(ControllerState.CAPTURING),
            ControllerEvent.SPEECH_READY to setOf(ControllerState.THINKING),
            ControllerEvent.PLAYBACK_FINISHED to setOf(ControllerState.SPEAKING),
            ControllerEvent.PAUSE to setOf(ControllerState.STANDBY, ControllerState.CAPTURING, ControllerState.THINKING, ControllerState.SPEAKING),
            ControllerEvent.RESUME to setOf(ControllerState.PAUSED),
            ControllerEvent.STOP to ControllerState.entries.toSet(),
            ControllerEvent.FAILURE to ControllerState.entries.toSet(),
        )
        for (state in ControllerState.entries) for (event in ControllerEvent.entries) {
            assertEquals("$state/$event", state in edges.getValue(event), NativeController.nextState(state, event) != null)
        }
    }
    @Test fun invalidEventCannotChangeStateAndErrorIsTyped() {
        val c = NativeController()
        assertFalse(c.dispatch(ControllerEvent.SPEECH_READY)); assertEquals(ControllerState.STOPPED,c.state())
        for (e in listOf(ControllerEvent.START,ControllerEvent.SPEECH_DETECTED,ControllerEvent.ENDPOINT,ControllerEvent.SPEECH_READY,ControllerEvent.PLAYBACK_FINISHED)) assertTrue(c.dispatch(e,token=c.token()))
        assertEquals(ControllerState.STANDBY,c.state())
        c.dispatch(ControllerEvent.FAILURE,SafeError.TIMEOUT,c.token()); assertEquals(SafeError.TIMEOUT,c.error())
        c.dispatch(ControllerEvent.READY); assertNull(c.error())
    }
}
