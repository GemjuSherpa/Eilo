package com.eilo.foundation

import java.util.concurrent.Executor
import org.junit.Assert.*
import org.junit.Test

class RateCaptureTest {
    private class Worker:Executor{val tasks=ArrayDeque<Runnable>();override fun execute(command:Runnable){tasks.add(command)};fun run(){while(tasks.isNotEmpty())tasks.removeFirst().run()}}
    private class Backend:VadStream{var samples=0;var closes=0;var calls=0;var probability=0.95f;override fun process(pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation{val start=samples;samples+=count;calls++;return NativeVadObservation(probability,start,count,final)};override fun close(){closes++}}
    private fun feed(d:VadCaptureTransport,count:Int,rate:Int=48000)=d.submit(FloatArray(count),count,rate)
    @Test fun quiet48kHasExactlyFiveNormalizedSeconds(){
        val w=Worker();val b=Backend();b.probability=0.05f;val events=mutableListOf<VadCaptureOutcome>()
        val d=VadCaptureTransport(w,{true},{b},output={e,a->events.add(e);assertTrue(a())},sourceRate=48000)
        repeat(500){assertTrue(feed(d,480));w.run()};assertEquals(EndpointResult.NO_SPEECH,events.single().result);assertEquals(80000,events.single().totalSamples)
        assertEquals(80000,b.samples);assertEquals(1,b.closes);assertEquals(0,d.retainedSamples());d.close();w.run()
    }
    @Test fun rawTailNeverPadsEvidence(){
        for(n in listOf(1,2,7,4807)){
            val w=Worker();val b=Backend();val events=mutableListOf<VadCaptureOutcome>();val d=VadCaptureTransport(w,{true},{b},output={e,_->events.add(e)},sourceRate=48000)
            var start=0;while(start<n){val count=minOf(4800,n-start);assertTrue(feed(d,count));w.run();start+=count};d.finish();w.run()
            assertEquals(EndpointResult.INCOMPLETE,events.single().result);assertEquals(n/3,events.single().totalSamples);assertEquals(n/3,b.samples);d.close();w.run()
        }
    }
    @Test fun rateChangeAndRawQueueOverflowRevoke(){
        val w=Worker();val b=Backend();var failures=0;val d=VadCaptureTransport(w,{true},{b},failure={failures++},sourceRate=48000)
        assertTrue(feed(d,1536));w.run();assertEquals(1,b.calls);assertFalse(feed(d,320,16000));w.run();assertEquals(1,b.closes);assertEquals(1,failures)
        val overflow=VadCaptureTransport(w,{true},sourceRate=48000);repeat(4){assertTrue(feed(overflow,4800))};assertEquals(19200,overflow.retainedSamples())
        assertFalse(feed(overflow,1));assertEquals(0,overflow.retainedSamples());w.run()
    }
    @Test fun slot48kFeedsExactNormalizedAsrPrefix(){
        val w=Worker();val e=EffectsSpy();val c=testController(effects=e);c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token())
        val b=Backend();val s=VadCaptureSlot(48000);var asrSamples=0;var closes=0;val finals=mutableListOf<AsrText>();val events=mutableListOf<VadCaptureOutcome>()
        val a=object:AsrStream{override fun accept(pcm:FloatArray,count:Int){asrSamples+=count};override fun text(finish:Boolean)="synthetic question";override fun close(){closes++}}
        assertTrue(s.install(e,c,c.token()!!,w,{true},{b},{events.add(it)},openAsr={a},recognized={finals.add(it)},asrVerified={true}))
        repeat(34){i->b.probability=if(i<8)0.95f else 0.05f;s.submit(ShortArray(960),960,48000);w.run()}
        assertEquals(1,finals.size);assertEquals(10752,asrSamples);assertEquals(192,events.single().lastChunkConsumed);assertEquals(1,closes)
        assertTrue(c.finishRecognition(c.token()!!,finals.single(),null,active={true},accepted={fail("confidence invented")}));assertEquals(listOf(RecognitionPolicy.CLARIFICATION),e.clauses);s.close();w.run()
    }
}
