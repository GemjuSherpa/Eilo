package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test

class NativeEndpointTest {
    @Test fun nativeWindowsConfirmAt160msAndNeverEndSilenceEarly() {
        val d=EndpointDetector()
        repeat(4) { assertEquals(EndpointResult.CONTINUE,d.advanceNative(.95f,it*512,512,false));assertFalse(d.confirmedSpeech()) }
        d.advanceNative(.95f,2048,512,false);assertTrue(d.confirmedSpeech())
        repeat(15) { assertEquals(EndpointResult.CONTINUE,d.advanceNative(.05f,2560+it*512,512,false)) }
        assertEquals(EndpointResult.COMPLETE,d.advanceNative(.05f,10240,512,false))
        assertEquals(10752,d.elapsedSamples());assertEquals(0,d.nativeInputCapacity())
    }
    @Test fun noSpeechIsExactlyFiveSecondsWithoutPadding() {
        val d=EndpointDetector()
        repeat(156) { assertEquals(EndpointResult.CONTINUE,d.advanceNative(.05f,it*512,512,false)) }
        assertEquals(128,d.nativeInputCapacity())
        assertEquals(EndpointResult.NO_SPEECH,d.advanceNative(.05f,79872,128,true))
        assertEquals(80000,d.elapsedSamples());assertFalse(d.confirmedSpeech())
        val overshoot=EndpointDetector();repeat(156) { overshoot.advanceNative(.05f,it*512,512,false) }
        assertEquals(EndpointResult.INVALID,overshoot.advanceNative(.05f,79872,512,false));assertEquals(79872,overshoot.elapsedSamples())
    }
    @Test fun turnLimitAndEarlyEofDoNotInventCompletion() {
        val d=EndpointDetector();repeat(937) { assertEquals(EndpointResult.CONTINUE,d.advanceNative(.95f,it*512,512,false)) }
        assertEquals(256,d.nativeInputCapacity())
        assertEquals(EndpointResult.LIMIT,d.advanceNative(.95f,479744,256,true));assertEquals(480000,d.elapsedSamples())
        val eof=EndpointDetector();assertEquals(EndpointResult.INCOMPLETE,eof.advanceNative(.95f,0,7,true))
        assertEquals(7,eof.elapsedSamples());assertFalse(eof.confirmedSpeech())
        assertEquals(EndpointResult.INVALID,eof.advanceNative(.95f,7,512,false))
    }
    @Test fun badShapeDiscontinuitiesAndMixedClocksRevoke() {
        for ((start,count,final) in listOf(Triple(1,512,false),Triple(0,0,true),Triple(0,513,true),Triple(0,128,false),Triple(-1,512,false))) {
            val d=EndpointDetector();assertEquals(EndpointResult.INVALID,d.advanceNative(.9f,start,count,final));assertEquals(0,d.nativeInputCapacity())
        }
        val duplicate=EndpointDetector();duplicate.advanceNative(.9f,0,512,false)
        assertEquals(EndpointResult.INVALID,duplicate.advanceNative(.9f,0,512,false));assertEquals(512,duplicate.elapsedSamples())
        val legacy=EndpointDetector();legacy.advance(.9f)
        assertEquals(EndpointResult.INVALID,legacy.advanceNative(.9f,320,512,false))
        val native=EndpointDetector();native.advanceNative(.9f,0,512,false)
        assertEquals(EndpointResult.INVALID,native.advance(.9f));assertFalse(native.confirmedSpeech())
    }
    @Test fun unknownScoresResetSilenceAndHighRun() {
        val d=EndpointDetector();repeat(5) { d.advanceNative(.9f,it*512,512,false) }
        repeat(15) { d.advanceNative(.1f,d.elapsedSamples(),512,false) }
        d.advanceNative(.5f,d.elapsedSamples(),512,false)
        repeat(15) { assertEquals(EndpointResult.CONTINUE,d.advanceNative(.1f,d.elapsedSamples(),512,false)) }
        assertEquals(EndpointResult.COMPLETE,d.advanceNative(.1f,d.elapsedSamples(),512,false))
        val burst=EndpointDetector();repeat(4) { burst.advanceNative(.9f,it*512,512,false) }
        burst.advanceNative(.5f,2048,512,false);burst.advanceNative(.9f,2560,512,false);assertFalse(burst.confirmedSpeech())
    }
    @Test fun invalidScoresCannotAdvanceClock() {
        for(p in listOf(Float.NaN,Float.POSITIVE_INFINITY,-.1f,1.1f)) {
            val d=EndpointDetector();assertEquals(EndpointResult.INVALID,d.advanceNative(p,0,512,false));assertEquals(0,d.elapsedSamples())
        }
    }
    @Test fun defaultDeniedAndRevocationCannotReleaseDecision() {
        val frame=NativeVadObservation(.9f,0,512,false)
        val unavailable=NativeVadEndpointBridge();assertEquals(EndpointResult.INVALID,unavailable.consume(frame));assertEquals(0,unavailable.elapsedSamples())
        var calls=0;val revoked=NativeVadEndpointBridge { ++calls==1 }
        assertEquals(EndpointResult.INVALID,revoked.consume(frame));assertEquals(0,revoked.inputCapacity())
        assertEquals(EndpointResult.INVALID,revoked.consume(frame));assertEquals(2,calls)
        val throwing=NativeVadEndpointBridge { error("revoked") }
        assertEquals(EndpointResult.INVALID,throwing.consume(frame));assertEquals(0,throwing.elapsedSamples())
    }
    @Test fun closingAndFinalAreTerminal() {
        val b=NativeVadEndpointBridge { true }
        assertEquals(EndpointResult.INCOMPLETE,b.consume(NativeVadObservation(.1f,0,5,true)))
        assertEquals(0,b.inputCapacity());b.close();b.close()
        assertEquals(EndpointResult.INVALID,b.consume(NativeVadObservation(.9f,5,512,false)))
    }
    @Test fun capacityCannotOpenOrReviveARevokedLease() {
        assertEquals(0,NativeVadEndpointBridge().inputCapacity())
        var valid=true;val b=NativeVadEndpointBridge { valid }
        assertEquals(512,b.inputCapacity());valid=false;assertEquals(0,b.inputCapacity())
        valid=true;assertEquals(0,b.inputCapacity())
    }
    @Test fun revocationAtCompletionWithholdsDecision() {
        var checks=0;val b=NativeVadEndpointBridge { ++checks<42 }
        repeat(20) { assertEquals(EndpointResult.CONTINUE,b.consume(NativeVadObservation(if(it<5) .9f else .1f,it*512,512,false))) }
        assertEquals(EndpointResult.INVALID,b.consume(NativeVadObservation(.1f,10240,512,false)))
        assertEquals(0,b.inputCapacity())
    }

}
