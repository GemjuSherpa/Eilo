package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
internal class FakePermission(var value: MicrophonePermission = MicrophonePermission.GRANTED) : MicrophonePermissionAdapter {
    var requests=0; var callback: ((MicrophonePermission) -> Unit)? = null
    override fun status()=value
    override fun request(completion: (MicrophonePermission) -> Unit) { requests++; callback=completion }
    fun complete(value: MicrophonePermission) { this.value=value; callback?.invoke(value) }
}
internal fun testController(diagnostics: SafeDiagnostics=SafeDiagnostics(),effects: ControllerEffects=EffectsSpy(),privateGate: PrivateEffectGate=PrivateEffectGate { false },clock: NativeClock=FakeTime(),scheduler: IdleScheduler=FakeTime(),permission: MicrophonePermissionAdapter=FakePermission()) = NativeController(diagnostics,effects,privateGate,clock,scheduler,permission)
class PermissionGateTest {
    @Test fun matrixRequiresExplicitStartAndDenialDoesNotLoop() {
        for (status in MicrophonePermission.entries) {
            val p=FakePermission(status); val spy=EffectsSpy(); val c=testController(effects=spy,permission=p)
            assertEquals(0,p.requests); assertEquals(0,spy.started)
            c.dispatch(ControllerEvent.START)
            assertEquals(if (status == MicrophonePermission.GRANTED) 1 else 0,spy.started)
            if (status == MicrophonePermission.NOT_REQUESTED) {
                assertEquals(1,p.requests); p.complete(MicrophonePermission.DENIED)
                repeat(3) { c.dispatch(ControllerEvent.START) }; assertEquals(1,p.requests); assertEquals(0,spy.started)
            }
        }
    }
    @Test fun lateGrantAfterStopAndDuplicateCallbackNeverCapture() {
        val p=FakePermission(MicrophonePermission.NOT_REQUESTED); val spy=EffectsSpy(); val c=testController(effects=spy,permission=p)
        c.dispatch(ControllerEvent.START); c.stop(); p.complete(MicrophonePermission.GRANTED)
        assertEquals(0,spy.started); assertEquals(ControllerState.STOPPED,c.state())
        c.dispatch(ControllerEvent.START); p.complete(MicrophonePermission.GRANTED); assertEquals(1,spy.started)
    }
    @Test fun revocationStopsAndRejectsPendingOutput() {
        val p=FakePermission(); val spy=EffectsSpy(); val c=testController(effects=spy,permission=p)
        c.dispatch(ControllerEvent.START); c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token()); c.dispatch(ControllerEvent.ENDPOINT,token=c.token()); val old=c.token()!!
        p.value=MicrophonePermission.DENIED; assertFalse(c.releaseSpeech(old,"revoked")); assertEquals(1,spy.released); assertTrue(spy.clauses.isEmpty()); assertEquals(ControllerState.STOPPED,c.state())
    }
    @Test fun pendingRepeatedStartAndReentrantStop() {
        val p=FakePermission(MicrophonePermission.NOT_REQUESTED); val spy=EffectsSpy(); val c=testController(effects=spy,permission=p)
        c.dispatch(ControllerEvent.START); assertFalse(c.dispatch(ControllerEvent.START)); p.complete(MicrophonePermission.GRANTED); assertEquals(1,spy.started)
        c.stop(); spy.onStart={ c.stop() }; assertFalse(c.dispatch(ControllerEvent.START)); assertEquals(ControllerState.STOPPED,c.state()); assertNull(c.token())
    }
    @Test fun missingProductionAdaptersFailClosed() {
        val spy=EffectsSpy(); val c=NativeController(effects=spy)
        assertFalse(c.dispatch(ControllerEvent.START)); assertEquals(0,spy.started)
    }
}
