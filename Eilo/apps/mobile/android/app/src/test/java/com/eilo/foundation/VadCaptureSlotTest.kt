package com.eilo.foundation

import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executor
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import org.junit.Assert.*
import org.junit.Test

class VadCaptureSlotTest {
    private class Worker:Executor {
        val tasks=ArrayDeque<Runnable>()
        override fun execute(command:Runnable){tasks.add(command)}
        fun run(){while(tasks.isNotEmpty())tasks.removeFirst().run()}
    }
    private class Backend:VadStream {
        var samples=0;var closes=0;var processing:()->Unit={}
        override fun process(pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation {
            val start=samples;samples+=count;processing();return NativeVadObservation(0.95f,start,count,final)
        }
        override fun close(){closes++}
    }
    private fun capturing(e:ControllerEffects):NativeController {
        val c=testController(effects=e);assertTrue(c.dispatch(ControllerEvent.START));assertTrue(c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token()));return c
    }
    private fun submit(slot:VadCaptureSlot,count:Int=320){slot.submit(ShortArray(count),count,16000)}
    @Test fun defaultsWrongCaptureAndStandbyDenyWithoutOpen() {
        val w=Worker();val e=EffectsSpy();val c=capturing(EffectsSpy());val slot=VadCaptureSlot(16000);var opens=0
        assertFalse(slot.install(e,c,c.token()!!,w,{true},{opens++;Backend()}))
        val own=capturing(e);assertFalse(slot.install(e,own,own.token()!!,w,open={opens++;Backend()}))
        val standby=testController(effects=e);standby.dispatch(ControllerEvent.START)
        assertFalse(slot.install(e,standby,standby.token()!!,w,{true}));w.run();assertEquals(0,opens)
    }
    @Test fun eofReleasesOnlyOneMetadataOutcomeAndRetiresPermit() {
        val w=Worker();val e=EffectsSpy();val b=Backend();val slot=VadCaptureSlot(16000);val c=capturing(e)
        val events=mutableListOf<VadCaptureOutcome>()
        assertTrue(slot.install(e,c,c.token()!!,w,{true},{b},{events.add(it)}))
        submit(slot,7);slot.finish();w.run();assertEquals(VadCaptureOutcome(EndpointResult.INCOMPLETE,7,0),events.single())
        assertEquals(ControllerState.CAPTURING,c.state());assertEquals(1,b.closes)
        slot.finish();w.run();assertEquals(1,events.size)
        assertTrue(slot.install(e,c,c.token()!!,w,{true}));slot.close();w.run()
    }
    @Test fun stopPausePrivacyInterruptionAndStateExitRejectQueuedWork() {
        repeat(5){phase->
            val w=Worker();val e=EffectsSpy();val c=capturing(e);val token=c.token()!!;val slot=VadCaptureSlot(16000)
            var opens=0;var events=0
            assertTrue(slot.install(e,c,token,w,{true},{opens++;Backend()},{events++}));submit(slot,512)
            when(phase){0->c.stop();1->c.dispatch(ControllerEvent.PAUSE);2->c.privacyTransition(PrivacyChange.LOCK);3->AudioInterruptionHandler(c).receive(AudioInterruption.ENGINE_RESET);else->c.dispatch(ControllerEvent.ENDPOINT,token=token)}
            w.run();assertEquals(0,opens);assertEquals(0,events)
        }
    }
    @Test fun modelRevocationDuringInferenceFailsSafely() {
        val w=Worker();val e=EffectsSpy();val c=capturing(e);val slot=VadCaptureSlot(16000);val b=Backend()
        var verified=true;var events=0;b.processing={verified=false}
        assertTrue(slot.install(e,c,c.token()!!,w,{verified},{b},{events++}));submit(slot,512);w.run()
        assertEquals(0,events);assertEquals(1,b.closes);assertEquals(ControllerState.ERROR,c.state());assertEquals(SafeError.UNAVAILABLE,c.error())
    }
    @Test fun detachClosedSlotAndOldTokenCannotRevive() {
        val w=Worker();val e=EffectsSpy();val c=capturing(e);val slot=VadCaptureSlot(16000);val b=Backend();val old=c.token()!!
        assertTrue(slot.install(e,c,old,w,{true},{b}));submit(slot,512);w.run();slot.detach();assertEquals(0,b.closes);w.run();assertEquals(1,b.closes)
        c.stop();c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token())
        assertFalse(slot.install(e,c,old,w,{true}));slot.close();assertFalse(slot.install(e,c,c.token()!!,w,{true}));w.run()
    }
    @Test fun stopDoesNotWaitForBlockedInference() {
        val worker=Executors.newSingleThreadExecutor();val entered=CountDownLatch(1);val release=CountDownLatch(1)
        val e=EffectsSpy();val c=capturing(e);val slot=VadCaptureSlot(16000);val b=Backend()
        b.processing={entered.countDown();check(release.await(5,TimeUnit.SECONDS))}
        try {
            assertTrue(slot.install(e,c,c.token()!!,worker,{true},{b},{fail("stale outcome")}));submit(slot,512)
            assertTrue(entered.await(5,TimeUnit.SECONDS));assertTrue(c.stop());release.countDown()
            worker.submit{}.get(5,TimeUnit.SECONDS);assertEquals(1,b.closes)
        } finally {release.countDown();slot.close();worker.shutdown();assertTrue(worker.awaitTermination(5,TimeUnit.SECONDS))}
    }
    @Test fun unsupportedRouteAndRevokedSetupCannotAttach() {
        val w=Worker();val e=EffectsSpy();val c=capturing(e)
        assertFalse(VadCaptureSlot(44100).install(e,c,c.token()!!,w,{true}))
        val slot=VadCaptureSlot(16000);var checks=0
        assertFalse(slot.install(e,c,c.token()!!,w,{checks++;if(checks==2)slot.close();true}));w.run()
        assertEquals(ControllerState.CAPTURING,c.state())
    }
    @Test fun preparedTicketCannotSurviveDetachOrBeReusedAndRevokesOnce() {
        val w=Worker();val e=EffectsSpy();val c=capturing(e);val slot=VadCaptureSlot(16000)
        val stale=slot.prepare(e,c,c.token()!!)!!;slot.detach();assertFalse(stale.current())
        assertFalse(slot.install(e,c,c.token()!!,w,{true},setup=stale))
        val fresh=slot.prepare(e,c,c.token()!!)!!;var revocations=0
        assertTrue(slot.install(e,c,c.token()!!,w,{true},setup=fresh,revoked={revocations++}))
        assertFalse(fresh.current());assertTrue(c.stop());assertEquals(1,revocations)
        slot.detach();w.run();assertEquals(1,revocations)
    }

    @Test fun failedTerminalStillReleasesOwnership() {
        val w=Worker();val e=EffectsSpy();val c=capturing(e);val slot=VadCaptureSlot(16000);val b=Backend()
        var valid=true;var revocations=0;b.processing={valid=false}
        assertTrue(slot.install(e,c,c.token()!!,w,{valid},{b},revoked={revocations++}))
        submit(slot,512);w.run();assertEquals(1,revocations);assertEquals(1,b.closes)
        valid=true;val fresh=capturing(e);assertNotNull(slot.prepare(e,fresh,fresh.token()!!))
        slot.close();w.run();assertEquals(1,revocations)
    }

}
