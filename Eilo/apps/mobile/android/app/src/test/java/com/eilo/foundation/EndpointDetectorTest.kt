package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class EndpointDetectorTest {
 @Test fun speechEndsAfterExactly500MillisecondsOfSilence(){val d=EndpointDetector();repeat(7){assertEquals(EndpointResult.CONTINUE,d.advance(.95f));assertFalse(d.confirmedSpeech())};d.advance(.95f);assertTrue(d.confirmedSpeech());repeat(24){assertEquals(EndpointResult.CONTINUE,d.advance(.05f))};assertEquals(EndpointResult.COMPLETE,d.advance(.05f));assertEquals(EndpointResult.INVALID,d.advance(.95f))}
 @Test fun noiseSilenceAndOverlapDoNotInventAnUtterance(){for(p in listOf(.05f,.4f)){val d=EndpointDetector();repeat(249){assertEquals(EndpointResult.CONTINUE,d.advance(p))};assertEquals(EndpointResult.NO_SPEECH,d.advance(p));assertFalse(d.confirmedSpeech())}}
 @Test fun pauseOverlapAndMaximumDurationAreBounded(){val d=EndpointDetector();repeat(8){d.advance(.95f)};repeat(20){d.advance(.05f)};d.advance(.5f);repeat(24){assertEquals(EndpointResult.CONTINUE,d.advance(.05f))};assertEquals(EndpointResult.COMPLETE,d.advance(.05f));val long=EndpointDetector();repeat(1499){assertEquals(EndpointResult.CONTINUE,long.advance(.95f))};assertEquals(EndpointResult.LIMIT,long.advance(.95f));assertEquals(480000,long.elapsedSamples())}
 @Test fun invalidProbabilityOrFrameFailsClosed(){for(p in listOf(Float.NaN,-.1f,1.1f)){assertEquals(EndpointResult.INVALID,EndpointDetector().advance(p))};assertEquals(EndpointResult.INVALID,EndpointDetector().advance(.95f,160))}
}
