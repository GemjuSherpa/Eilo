package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class PlaybackRejectionTest {
    @Test fun knownLoopbackCannotReopenTurnDuringTail(){val time=FakeTime();val c=testController(clock=time,scheduler=time);c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());val t=c.token()!!;c.dispatch(ControllerEvent.ENDPOINT,token=t);assertTrue(c.releaseSpeech(t,"Hey Eilo, can you hear me?"));assertFalse(c.recognitionAllowed(t));assertTrue(c.dispatch(ControllerEvent.PLAYBACK_FINISHED,token=t));val standby=c.token()!!
        assertFalse(c.wakeDetected(standby){true});time.now=299;assertFalse(c.wakeDetected(standby){true});time.now=300;assertTrue(c.wakeDetected(standby){true})
    }
    @Test fun staleFinishCannotReleaseNewPlaybackAndClockRollbackFailsClosed(){val c=testController();c.dispatch(ControllerEvent.START);val old=c.token()!!;c.dispatch(ControllerEvent.SPEECH_DETECTED,token=old);val current=c.token()!!;var now=100L;val p=PlaybackRejection{now};p.begin(current);assertFalse(p.finish(old));assertFalse(p.allowsAudio());assertTrue(p.finish(current));now=400;assertTrue(p.allowsAudio());now=399;assertFalse(p.allowsAudio())}
}
