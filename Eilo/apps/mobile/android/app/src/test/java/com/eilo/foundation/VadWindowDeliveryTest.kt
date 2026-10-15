package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test

class VadWindowDeliveryTest {
    private class Backend:VadStream {
        val received=mutableListOf<Float>();val counts=mutableListOf<Int>();val finals=mutableListOf<Boolean>()
        var closes=0;var probability=.95f;var wrong=false;var onProcess:()->Unit={};var onClose:()->Unit={}
        override fun process(pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation {
            val start=received.size;received.addAll(pcm.take(count));counts+=count;finals+=final;onProcess()
            return NativeVadObservation(probability,if(wrong) start+1 else start,count,final)
        }
        override fun close(){closes++;onClose()}
    }
    private fun feed(d:VadWindowDelivery,count:Int=320,start:Int,value:Float=0f)=d.accept(FloatArray(count){value},count,start)
    @Test fun chunksCopyInOrderAndOnlyRealTailIsFinalized() {
        val b=Backend();var opens=0;val d=VadWindowDelivery({true},{opens++;b});val expected=mutableListOf<Float>()
        repeat(20) { chunk ->
            val pcm=FloatArray(320){((chunk*320+it)%1000)/1000f};expected.addAll(pcm.toList())
            val event=d.accept(pcm,320,chunk*320);assertEquals(EndpointResult.CONTINUE,event.result);assertEquals(320,event.consumedSamples)
            pcm.fill(-.9f);assertTrue(d.retainedSamples()<512)
        }
        assertEquals(1,opens);assertEquals(256,d.retainedSamples());assertEquals(EndpointResult.INCOMPLETE,d.finish().result)
        assertEquals(expected,b.received);assertEquals(List(12){512}+256,b.counts);assertEquals(List(12){false}+true,b.finals)
        assertEquals(0,d.retainedSamples());d.close();assertEquals(1,b.closes)
    }
    @Test fun silenceBudgetIsExactlyFiveSecondsWith128SampleTail() {
        val b=Backend();b.probability=.05f;val d=VadWindowDelivery({true},{b})
        repeat(249){assertEquals(EndpointResult.CONTINUE,feed(d,start=it*320).result)}
        val event=feed(d,start=79680);assertEquals(EndpointResult.NO_SPEECH,event.result);assertEquals(320,event.consumedSamples)
        assertEquals(80000,d.acceptedSamples());assertEquals(157,b.counts.size);assertEquals(128,b.counts.last())
        assertTrue(b.finals.last());assertEquals(80000,b.received.size);assertEquals(1,b.closes)
    }
    @Test fun endpointConsumesOnlyPrefixOfLastCallback() {
        val b=Backend();val d=VadWindowDelivery({true},{b})
        repeat(33){b.probability=if(it<8) .95f else .05f;assertEquals(EndpointResult.CONTINUE,feed(d,start=it*320).result)}
        val event=feed(d,start=10560);assertEquals(EndpointResult.COMPLETE,event.result);assertEquals(192,event.consumedSamples)
        assertEquals(10752,d.acceptedSamples());assertEquals(10752,b.received.size)
        assertEquals(EndpointResult.INVALID,feed(d,start=10752).result);assertEquals(1,b.closes)
    }
    @Test fun continuousSpeechStopsExactlyAtThirtySeconds() {
        val b=Backend();val d=VadWindowDelivery({true},{b})
        repeat(1499){assertEquals(EndpointResult.CONTINUE,feed(d,start=it*320).result)}
        assertEquals(EndpointResult.LIMIT,feed(d,start=479680).result);assertEquals(480000,b.received.size)
        assertEquals(256,b.counts.last());assertEquals(1,b.closes);assertEquals(0,d.retainedSamples())
    }
    @Test fun revokedPendingDataNeverOpensOrRevives() {
        var valid=true;var opens=0;val b=Backend();val d=VadWindowDelivery({valid},{opens++;b})
        assertEquals(EndpointResult.CONTINUE,feed(d,start=0).result);assertEquals(320,d.retainedSamples())
        valid=false;assertEquals(EndpointResult.INVALID,feed(d,start=320).result);assertEquals(0,d.retainedSamples());assertEquals(0,opens)
        valid=true;assertEquals(EndpointResult.INVALID,feed(d,start=320).result)
        val denied=VadWindowDelivery();assertEquals(EndpointResult.INVALID,feed(denied,start=0).result);assertEquals(0,denied.retainedSamples())
    }
    @Test fun revocationAtOpenOrDecodeCannotReleaseEvent() {
        repeat(3){phase ->
            var valid=true;val b=Backend();if(phase==1)b.onProcess={valid=false}
            val d=VadWindowDelivery({valid},{if(phase==0)valid=false;b});if(phase==2)valid=false
            val event=feed(d,512,start=0);assertEquals(EndpointResult.INVALID,event.result);assertEquals(0,event.consumedSamples)
            assertEquals(0,d.retainedSamples());assertEquals(if(phase==2)0 else 1,b.closes)
        }
    }
    @Test fun invalidInputDiscontinuityAndBadNativeFrameAreTerminal() {
        for((start,count,value) in listOf(Triple(1,320,0f),Triple(0,0,0f),Triple(0,1601,0f),Triple(0,320,Float.NaN),Triple(0,320,1.1f))) {
            val b=Backend();val d=VadWindowDelivery({true},{b});assertEquals(EndpointResult.INVALID,feed(d,count,start,value).result)
            assertEquals(0,d.retainedSamples());assertTrue(b.received.isEmpty())
        }
        val b=Backend();b.wrong=true;val d=VadWindowDelivery({true},{b});assertEquals(EndpointResult.INVALID,feed(d,512,start=0).result);assertEquals(1,b.closes)
        val duplicate=VadWindowDelivery({true},{Backend()});feed(duplicate,start=0)
        assertEquals(EndpointResult.INVALID,feed(duplicate,start=0).result)
    }
    @Test fun emptyAndExactWindowEofDoNotInventTailFrames() {
        var opens=0;val b=Backend();val empty=VadWindowDelivery({true},{opens++;b})
        assertEquals(EndpointResult.INCOMPLETE,empty.finish().result);assertEquals(0,opens)
        val full=VadWindowDelivery({true},{b});feed(full,512,start=0)
        assertEquals(EndpointResult.INCOMPLETE,full.finish().result);assertEquals(listOf(512),b.counts);assertEquals(listOf(false),b.finals)
        assertEquals(EndpointResult.INVALID,full.finish().result);assertEquals(1,b.closes)
    }
    @Test fun revocationDuringCleanupWithholdsFinalEvent() {
        var valid=true;val b=Backend();val d=VadWindowDelivery({valid},{b})
        assertEquals(EndpointResult.CONTINUE,feed(d,7,start=0).result)
        b.onClose={valid=false};assertEquals(EndpointResult.INVALID,d.finish().result)
        assertEquals(0,d.retainedSamples());assertEquals(1,b.closes)
        valid=true;assertEquals(EndpointResult.INVALID,d.finish().result)
    }

}
