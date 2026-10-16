package com.eilo.foundation

import kotlin.math.*
import org.junit.Assert.*
import org.junit.Test

class StreamingRateConverterTest {
    private fun convert(input:FloatArray,sizes:List<Int>,rate:Int=48000):List<Float> {
        val c=StreamingRateConverter(rate);val output=mutableListOf<Float>();var offset=0;var index=0
        while(offset<input.size){val n=minOf(sizes[index%sizes.size],input.size-offset);c.convert(input.copyOfRange(offset,offset+n),n){pcm,count->output.addAll(pcm.take(count))};offset+=n;index++}
        assertEquals(if(rate==48000)input.size%3 else 0,c.pendingSourceSamples());c.close();assertEquals(0,c.pendingSourceSamples());return output
    }
    @Test fun passThroughPreservesFloatBits(){val input=floatArrayOf(0f,-0f,0.1234567f,-1f,1f);assertEquals(input.map{it.toRawBits()},convert(input,listOf(1,2),16000).map{it.toRawBits()})}
    @Test fun chunksPreservePhaseAndFloorDuration(){val input=FloatArray(4807){(sin(it*0.13)*0.5).toFloat()};val a=convert(input,listOf(4800));assertEquals(1602,a.size);assertEquals(a,convert(input,listOf(1,2,5,511,7,320)))}
    @Test fun passbandAndAliasRejection(){
        fun rms(hz:Double):Double {val output=convert(FloatArray(9600){(0.5*sin(2*PI*hz*it/48000)).toFloat()},listOf(512,17,1,4800)).drop(100);return sqrt(output.sumOf{it.toDouble()*it}/output.size)}
        val pass=rms(1000.0);assertEquals(0.5/sqrt(2.0),pass,0.001);assertTrue(rms(10000.0)/pass<0.0031623)
    }
    @Test fun invalidBoundsRateSamplesAndClosedStreamReject(){
        assertThrows(IllegalArgumentException::class.java){StreamingRateConverter(44100)}
        for(input in listOf(floatArrayOf(),floatArrayOf(Float.NaN),floatArrayOf(1.1f),FloatArray(4801))){
            val c=StreamingRateConverter(48000);assertThrows(IllegalStateException::class.java){c.convert(input,input.size){_,_->fail("invalid output")}}
            assertEquals(0,c.pendingSourceSamples());assertThrows(IllegalStateException::class.java){c.convert(FloatArray(3),3){_,_->fail("revived")}}
        }
    }
    @Test fun tailNeverPadsAndConsumerFailureCloses(){
        val c=StreamingRateConverter(48000);var calls=0;c.convert(FloatArray(2){1f},2){_,_->calls++};assertEquals(0,calls);assertEquals(2,c.pendingSourceSamples());c.close();assertEquals(0,c.pendingSourceSamples())
        val failed=StreamingRateConverter(48000);assertThrows(IllegalStateException::class.java){failed.convert(FloatArray(3),3){_,_->error("synthetic failure")}}
        assertThrows(IllegalStateException::class.java){failed.convert(FloatArray(3),3){_,_->}}
    }
}
