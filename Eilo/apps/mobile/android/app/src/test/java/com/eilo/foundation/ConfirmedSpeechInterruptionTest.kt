package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class ConfirmedSpeechInterruptionTest {
    @Test fun noiseShortBurstsAndOwnOutputDoNotCancelButConfirmedSpeechDoes(){
        val time=FakeTime();var canceledAt:Long?=null;val clauses=mutableListOf<String>()
        val c=testController(clock=time,scheduler=time,effects=object:ControllerEffects{override fun startCapture()=true;override fun playClause(clause:String){clauses.add(clause)};override fun cancelWork(){canceledAt=time.now};override fun releaseCapture(){};override fun clearVolatileContext(){}})
        c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());val old=c.token()!!;c.dispatch(ControllerEvent.ENDPOINT,token=old);c.releaseSpeech(old,"reply")
        val d=ConfirmedSpeechInterruption(old)
        repeat(30){assertNull(d.advance(.5f,true));assertNull(d.advance(.95f,false))};repeat(7){assertNull(d.advance(.95f,true))};assertNull(d.advance(.05f,true));assertNull(canceledAt)
        repeat(7){time.now+=20;assertNull(d.advance(.95f,true))};time.now+=20;val event=d.advance(.95f,true)!!
        val current=event.apply(c){true};assertNotNull(current);assertEquals(160L,canceledAt);assertTrue(old.cancelled);assertEquals(ControllerState.CAPTURING,c.state());assertFalse(c.releaseSpeech(old,"stale queued clause"));assertEquals(listOf("reply"),clauses);assertNull(event.apply(c){true})
    }
    @Test fun revocationAndReentrantStopCannotCreateReplacement(){val effects=EffectsSpy();val c=testController(effects=effects);c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());val t=c.token()!!;c.dispatch(ControllerEvent.ENDPOINT,token=t)
        assertNull(c.interruptReply(t){false});assertFalse(t.cancelled);effects.onCancel={c.stop()};assertNull(c.interruptReply(t){true});assertEquals(ControllerState.STOPPED,c.state());assertNull(c.token())
    }
}
