package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test

class VadAsrHandoffTest {
    private class Backend:AsrStream {
        val pcm=mutableListOf<Float>();var closes=0;var finals=0
        var onAccept:()->Unit={};var onFinal:()->Unit={};var onClose:()->Unit={}
        override fun accept(pcm:FloatArray,count:Int){this.pcm.addAll(pcm.take(count));onAccept()}
        override fun text(finish:Boolean):String{if(finish){finals++;onFinal()};return "synthetic question"}
        override fun close(){closes++;onClose()}
    }
    private fun token():GenerationToken {val c=testController();c.dispatch(ControllerEvent.START);return c.token()!!}
    private fun append(h:VadAsrHandoff,count:Int=320,consumed:Int=count,start:Int,value:Float=0f)=h.append(FloatArray(count){value},count,consumed,start)
    @Test fun exactPrefixCopiesAndFinalExcludesSuffix() {
        val b=Backend();var opens=0;val h=VadAsrHandoff(token(),{true},{opens++;b})
        repeat(33){assertTrue(append(h,start=it*320,value=0.1234567f))}
        val pcm=FloatArray(320){0.75f};assertTrue(h.append(pcm,320,192,10560));pcm.fill(-1f)
        assertEquals(0,opens);assertEquals(10752,h.retainedSamples())
        assertEquals(VadAsrFinal.Recognized(AsrText("synthetic question",true)),h.finish(VadCaptureOutcome(EndpointResult.COMPLETE,10752,192)))
        assertEquals(List(10560){0.1234567f}+List(192){0.75f},b.pcm);assertEquals(1,opens);assertEquals(1,b.finals);assertEquals(1,b.closes);assertEquals(0,h.retainedSamples())
        assertEquals(VadAsrFinal.Invalid,h.finish(VadCaptureOutcome(EndpointResult.COMPLETE,10752,192)))
    }
    @Test fun silenceAndIncompleteNeverOpenAsr() {
        for(n in listOf(0,7,80000)) {
            var opens=0;val h=VadAsrHandoff(token(),{true},{opens++;Backend()});var start=0
            while(start<n){val take=minOf(1600,n-start);assertTrue(append(h,take,start=start));start+=take}
            assertEquals(VadAsrFinal.Metadata,h.finish(VadCaptureOutcome(if(n==80000)EndpointResult.NO_SPEECH else EndpointResult.INCOMPLETE,n,0)))
            assertEquals(0,opens);assertEquals(0,h.retainedSamples())
        }
    }
    @Test fun thirtySecondCapAndOverflowCannotExtendAudio() {
        val b=Backend();val h=VadAsrHandoff(token(),{true},{b})
        for(start in 0 until 480000 step 1600)assertTrue(append(h,1600,start=start))
        assertTrue(h.finish(VadCaptureOutcome(EndpointResult.LIMIT,480000,1600)) is VadAsrFinal.Recognized)
        assertEquals(480000,b.pcm.size);assertEquals(1,b.closes)
        val overflow=VadAsrHandoff(token(),{true},{Backend()})
        for(start in 0 until 480000 step 1600)assertTrue(append(overflow,1600,start=start))
        assertFalse(append(overflow,1,start=480000));assertEquals(0,overflow.retainedSamples())
    }
    @Test fun malformedDiscontinuousInputClearsTerminally() {
        for(kind in 0..5) {
            val h=VadAsrHandoff(token(),{true},{Backend()})
            val accepted=when(kind){0->append(h,start=1);1->append(h,consumed=0,start=0);2->append(h,consumed=321,start=0);3->append(h,1601,start=0);4->append(h,start=0,value=Float.NaN);else->h.append(FloatArray(2),3,2,0)}
            assertFalse(accepted);assertEquals(0,h.retainedSamples());assertFalse(append(h,start=0))
        }
    }
    @Test fun badOutcomeNeverInventsText() {
        for(r in listOf(EndpointResult.CONTINUE,EndpointResult.INVALID,EndpointResult.NO_SPEECH,EndpointResult.LIMIT)) {
            var opens=0;val h=VadAsrHandoff(token(),{true},{opens++;Backend()});assertTrue(append(h,start=0))
            assertEquals(VadAsrFinal.Invalid,h.finish(VadCaptureOutcome(r,320,320)));assertEquals(0,opens);assertEquals(0,h.retainedSamples())
        }
    }
    @Test fun revocationAtAcceptFinalAndCleanupWithholdsText() {
        repeat(3){phase->
            var valid=true;val b=Backend();val h=VadAsrHandoff(token(),{valid},{b})
            repeat(34){assertTrue(append(h,if(it==33)192 else 320,start=it*320))}
            when(phase){0->b.onAccept={valid=false};1->b.onFinal={valid=false};else->b.onClose={valid=false}}
            assertEquals(VadAsrFinal.Invalid,h.finish(VadCaptureOutcome(EndpointResult.COMPLETE,10752,192)));assertEquals(1,b.closes);assertEquals(0,h.retainedSamples())
        }
    }
    @Test fun deniedOrRevokedTokenNeverOpens() {
        val c=testController();c.dispatch(ControllerEvent.START);val t=c.token()!!;c.stop()
        val h=VadAsrHandoff(t,{true},{fail("revoked open");Backend()});assertFalse(append(h,start=0));assertEquals(0,h.retainedSamples())
        assertFalse(append(VadAsrHandoff(token(),{false},{Backend()}),start=0))
    }
}
