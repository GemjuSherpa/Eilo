package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
internal class FakeTime : NativeClock, IdleScheduler {
    var now=0L
    class Job(val delay: Long,val task: () -> Unit) { var cancelled=false }
    val jobs=mutableListOf<Job>()
    override fun milliseconds()=now
    override fun schedule(delayMilliseconds: Long,task: () -> Unit): IdleCancellation { val job=Job(delayMilliseconds,task); jobs.add(job); return IdleCancellation { job.cancelled=true } }
}
class IdleTimerTest {
    @Test fun processingPlaybackDeferAndSixtySecondsOfIdleClearsOnlyContext() {
        val time=FakeTime(); val spy=EffectsSpy(); val c=NativeController(effects=spy,clock=time,scheduler=time)
        c.dispatch(ControllerEvent.START); assertTrue(time.jobs.isEmpty())
        c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token()); c.dispatch(ControllerEvent.ENDPOINT,token=c.token())
        time.now=120_000; assertTrue(time.jobs.isEmpty()); assertEquals(ControllerState.THINKING,c.state())
        c.releaseSpeech(c.token()!!,"synthetic"); time.now=240_000; assertTrue(time.jobs.isEmpty())
        c.dispatch(ControllerEvent.PLAYBACK_FINISHED,token=c.token()); val job=time.jobs.last()
        time.now+=59_999; job.task(); assertEquals(0,spy.cleared)
        time.now++; time.jobs.last().task(); assertEquals(1,spy.cleared); assertEquals(0,spy.released)
        assertEquals(ControllerState.STANDBY,c.state()); assertArrayEquals(byteArrayOf(4,5),spy.committedHistory)
    }
    @Test fun resumedSpeechAndStopInvalidateOldTimers() {
        val time=FakeTime(); val spy=EffectsSpy(); val c=NativeController(effects=spy,clock=time,scheduler=time)
        for (e in listOf(ControllerEvent.START,ControllerEvent.SPEECH_DETECTED,ControllerEvent.ENDPOINT,ControllerEvent.SPEECH_READY,ControllerEvent.PLAYBACK_FINISHED)) c.dispatch(e,token=c.token())
        val old=time.jobs.last(); c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token())
        assertTrue(old.cancelled); time.now=100_000; old.task(); assertEquals(ControllerState.CAPTURING,c.state()); assertEquals(0,spy.cleared)
        c.stop(); old.task(); assertEquals(ControllerState.STOPPED,c.state()); assertEquals(1,spy.cleared)
    }
}
