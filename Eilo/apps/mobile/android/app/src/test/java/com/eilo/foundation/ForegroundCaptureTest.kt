package com.eilo.foundation

import java.util.concurrent.Executor
import org.junit.Assert.*
import org.junit.Test

private class QueuedWorker : Executor {
    val tasks = ArrayDeque<Runnable>()
    override fun execute(command: Runnable) { tasks.add(command) }
    fun next() { tasks.removeFirst().run() }
}
private class DeviceSpy : CaptureDevice {
    var starts=0; var closes=0; var reads=0; var closed=false
    var onRead: (ShortArray) -> Int = { -1 }
    override fun start() { starts++ }
    override fun read(samples: ShortArray): Int { reads++; samples.fill(42); return onRead(samples) }
    override fun close() { if (!closed) { closed=true; closes++ } }
}
private class DeferredCapture : ControllerEffects {
    val completions=mutableListOf<(Boolean)->Unit>()
    val failures=mutableListOf<()->Unit>()
    var releases=0
    override fun startCapture() = error("asynchronous only")
    override fun beginCapture(completion: (Boolean)->Unit, failure: ()->Unit) { completions.add(completion); failures.add(failure) }
    override fun releaseCapture() { releases++ }
    override fun cancelWork() {}
    override fun clearVolatileContext() {}
    override fun playClause(clause: String) {}
}
class ForegroundCaptureTest {
    @Test fun pendingOpenHasNoGenerationAndRejectsDuplicateStart() {
        val e=DeferredCapture(); val c=testController(effects=e)
        assertTrue(c.dispatch(ControllerEvent.START)); assertNull(c.token())
        assertEquals(ControllerState.STOPPED,c.state())
        assertFalse(c.dispatch(ControllerEvent.START)); assertEquals(1,e.completions.size)
        e.completions[0](true)
        assertEquals(ControllerState.STANDBY,c.state()); assertNotNull(c.token())
        e.completions[0](true); assertEquals(ControllerState.STANDBY,c.state())
    }
    @Test fun stopRevocationAndOldFailureCannotReviveOrStopNewCapture() {
        val p=FakePermission(); val e=DeferredCapture(); val c=testController(effects=e,permission=p)
        c.dispatch(ControllerEvent.START); c.stop(); e.completions[0](true)
        assertEquals(ControllerState.STOPPED,c.state()); assertNull(c.token())
        c.dispatch(ControllerEvent.START); e.completions[1](true)
        e.failures[0](); assertEquals(ControllerState.STANDBY,c.state())
        c.stop(); c.dispatch(ControllerEvent.START); p.value=MicrophonePermission.DENIED
        e.completions[2](true); assertEquals(ControllerState.STOPPED,c.state()); assertNull(c.token())
    }
    @Test fun interveningSetupCannotBeOverriddenByDelayedCapture() {
        val e=DeferredCapture(); val c=testController(effects=e)
        c.dispatch(ControllerEvent.START); c.dispatch(ControllerEvent.SETUP_REQUIRED)
        e.completions[0](true)
        assertEquals(ControllerState.STOPPED,c.state()); assertNull(c.token()); assertEquals(1,e.releases)
    }
    @Test fun currentReadFailureReleasesAndInvalidatesGeneration() {
        val e=DeferredCapture(); val c=testController(effects=e)
        c.dispatch(ControllerEvent.START); e.completions[0](true); val token=c.token()!!
        e.failures[0](); assertEquals(ControllerState.ERROR,c.state()); assertTrue(token.cancelled)
        assertEquals(1,e.releases)
    }
    @Test fun noOpenOnConstructionOrInvisibleStart() {
        val w=QueuedWorker(); var opens=0
        val capture=ForegroundCapture(w,{false},{ opens++; DeviceSpy() })
        assertEquals(0,opens)
        var result: Boolean?=null
        capture.beginCapture({result=it},{fail("unexpected failure")})
        assertEquals(0,opens); w.next(); assertEquals(false,result); assertEquals(0,opens)
    }
    @Test fun exitDuringOpenClosesWithoutRecording() {
        val w=QueuedWorker(); val d=DeviceSpy(); var visible=true
        val capture=ForegroundCapture(w,{visible},{ visible=false; d })
        var result: Boolean?=null
        capture.beginCapture({result=it},{fail("unexpected failure")}); w.next()
        assertEquals(false,result); assertEquals(0,d.starts); assertEquals(1,d.closes)
    }
    @Test fun stopDuringOpenCancelsBeforeRecording() {
        val w=QueuedWorker(); val d=DeviceSpy(); lateinit var capture: ForegroundCapture
        capture=ForegroundCapture(w,{true},{ capture.releaseCapture(); d })
        capture.beginCapture({assertFalse(it)},{fail("unexpected failure")}); w.next()
        assertEquals(0,d.starts); assertEquals(1,d.closes)
    }
    @Test fun nativeReadFailureClearsSamplesAndClosesExactlyOnce() {
        val w=QueuedWorker(); val d=DeviceSpy(); lateinit var capture: ForegroundCapture
        capture=ForegroundCapture(w,{true},{d})
        var buffer: ShortArray?=null; var started=false; var failed=false
        d.onRead={ buffer=it; -1 }
        capture.beginCapture({started=it},{failed=true; capture.releaseCapture()}); w.next()
        assertTrue(started); assertTrue(failed); assertEquals(1,d.starts); assertEquals(1,d.closes)
        assertTrue(buffer!!.all { it==0.toShort() }); capture.releaseCapture(); assertEquals(1,d.closes)
    }
    @Test fun serviceLifecycleOnlyActivatesFromEligibleStartAndStopsOnFailure() {
        val w=QueuedWorker();val d=DeviceSpy();var activated=0;var deactivated=0
        lateinit var capture:ForegroundCapture
        capture=ForegroundCapture(w,{true},{d},{activated++},{deactivated++})
        assertEquals(0,activated)
        capture.beginCapture({assertTrue(it)},{capture.releaseCapture()});w.next()
        assertEquals(1,activated);assertEquals(1,deactivated);assertEquals(1,d.closes)
    }
    @Test fun constructionFailureIsGenericAndNeverReportsStarted() {
        val w=QueuedWorker(); val capture=ForegroundCapture(w,{true},{throw SecurityException()})
        var started=false; var failed=false
        capture.beginCapture({started=it},{failed=true}); w.next()
        assertFalse(started); assertTrue(failed)
    }
}
