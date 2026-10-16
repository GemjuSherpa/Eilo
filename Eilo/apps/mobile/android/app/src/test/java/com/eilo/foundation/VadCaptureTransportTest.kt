package com.eilo.foundation

import java.util.concurrent.Executor
import org.junit.Assert.*
import org.junit.Test

class VadCaptureTransportTest {
    private class Worker:Executor {
        val tasks=ArrayDeque<Runnable>()
        override fun execute(command:Runnable) { tasks.add(command) }
        fun run() { while(tasks.isNotEmpty())tasks.removeFirst().run() }
    }
    private class Backend:VadStream {
        val pcm=mutableListOf<Float>();var closes=0;var calls=0;var probability=0.95f
        var processing:()->Unit={}
        override fun process(pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation {
            val start=this.pcm.size;this.pcm.addAll(pcm.take(count));calls++;processing()
            return NativeVadObservation(probability,start,count,final)
        }
        override fun close() { closes++ }
    }
    private fun feed(d:VadCaptureTransport,count:Int=320,value:Float=0f,rate:Int=16000)=d.submit(FloatArray(count){value},count,rate)
    @Test fun copiedFramesCoalesceAndActualTailFinalizes() {
        val w=Worker();val b=Backend();val events=mutableListOf<VadCaptureOutcome>();var opens=0
        val d=VadCaptureTransport(w,{true},{opens++;b},output={e,active->events.add(e);assertTrue(active())})
        val pcm=FloatArray(320){0.25f};assertTrue(d.submit(pcm,320,16000));pcm.fill(-0.5f)
        assertTrue(feed(d,7,0.75f));d.finish();assertEquals(1,w.tasks.size);assertEquals(0,opens)
        assertEquals(327,d.retainedSamples());w.run()
        assertEquals(List(320){0.25f}+List(7){0.75f},b.pcm)
        assertEquals(EndpointResult.INCOMPLETE,events.single().result);assertEquals(327,events.single().totalSamples)
        assertEquals(1,b.closes);assertEquals(0,d.retainedSamples())
    }
    @Test fun overflowIsTerminalErasesWithoutOpening() {
        val w=Worker();var opens=0;var outputs=0
        val d=VadCaptureTransport(w,{true},{opens++;Backend()},output={_,_->outputs++})
        repeat(4){assertTrue(feed(d,1600))};assertEquals(6400,d.retainedSamples())
        assertFalse(feed(d));assertEquals(0,d.retainedSamples());assertEquals(1,w.tasks.size);w.run()
        assertEquals(0,opens);assertEquals(0,outputs);assertFalse(d.current());assertFalse(feed(d))
    }
    @Test fun malformedRateInputAndClockRegressionRevoke() {
        repeat(6){kind->
            val w=Worker();var time=100L;val d=VadCaptureTransport(w,{true},now={time})
            assertTrue(feed(d));if(kind==4)time=99
            val accepted=when(kind){0->feed(d,rate=48000);1->feed(d,1601);2->feed(d,value=Float.NaN);3->feed(d,0);4->feed(d);else->d.submit(FloatArray(2),3,16000)}
            assertFalse(accepted);assertEquals(0,d.retainedSamples());w.run();assertFalse(d.current())
        }
    }
    @Test fun ageBoundaryAndDeniedLeaseNeverOpen() {
        for(revoked in listOf(false,true)) {
            val w=Worker();var time=0L;var opens=0
            val d=VadCaptureTransport(w,{!revoked},{opens++;Backend()},now={time})
            assertTrue(feed(d,512));if(!revoked)time=250_000_000;w.run()
            assertEquals(0,opens);assertFalse(d.current());assertEquals(0,d.retainedSamples())
        }
    }
    @Test fun stopWithoutNewFramesSchedulesWorkerCleanup() {
        val w=Worker();val b=Backend();val d=VadCaptureTransport(w,{true},{b})
        assertTrue(feed(d,512));w.run();assertEquals(1,b.calls);assertEquals(0,b.closes)
        assertTrue(feed(d));d.close();assertEquals(0,d.retainedSamples());assertEquals(0,b.closes)
        assertEquals(1,w.tasks.size);w.run();assertEquals(1,b.closes);assertFalse(feed(d))
    }
    @Test fun stopDuringInferenceSuppressesResults() {
        val w=Worker();val b=Backend();var outputs=0
        val d=VadCaptureTransport(w,{true},{b},output={_,_->outputs++});b.processing={d.close()}
        assertTrue(feed(d,512));w.run();assertEquals(0,outputs);assertEquals(1,b.closes);assertFalse(feed(d))
    }
    @Test fun exactEndpointPrefixAndDelayedLease() {
        val w=Worker();val b=Backend();val events=mutableListOf<VadCaptureOutcome>();var active:(()->Boolean)?=null
        val d=VadCaptureTransport(w,{true},{b},output={e,a->events.add(e);active=a})
        repeat(34){i->b.probability=if(i<8)0.95f else 0.05f;assertTrue(feed(d));w.run()}
        assertEquals(VadCaptureOutcome(EndpointResult.COMPLETE,10752,192),events.single())
        assertTrue(active!!());d.close();assertFalse(active!!());w.run();assertEquals(10752,b.pcm.size);assertEquals(1,b.closes)
    }
    @Test fun pcm16ConversionUsesExactSignedScaleAndDoesNotRetainInput() {
        val w=Worker();val b=Backend();val d=VadCaptureTransport(w,{true},{b})
        val pcm=shortArrayOf(Short.MIN_VALUE,0,Short.MAX_VALUE);assertTrue(d.submit(pcm,3,16000));pcm.fill(1)
        d.finish();w.run();assertEquals(listOf(-1f,0f,32767f/32768),b.pcm)
    }
    @Test fun ownershipFinishesOnceOnIdleCancelAndNormalEof() {
        for(eof in listOf(false,true)) {
            val w=Worker();var disposals=0;val d=VadCaptureTransport(w,{true},finished={disposals++})
            if(eof)d.finish() else d.close();assertEquals(0,disposals)
            w.run();assertEquals(1,disposals);d.close();w.run();assertEquals(1,disposals)
        }
    }

}
