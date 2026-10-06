package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class StandbyAudioBufferTest {
 @Test fun streamKeepsOnlyTwoSecondsInOrderAcrossWraps() {
  var time=0L;val b=StandbyAudioBuffer(8000) { time };val ticket=b.begin()
  for(frame in 0..5) { time=frame*500_000_000L;b.append(ticket,ShortArray(4000) { frame.toShort() },4000) }
  assertEquals(16000,b.count());assertEquals(2.toShort(),b.sample(0));assertEquals(5.toShort(),b.sample(15999))
 }
 @Test fun oversizedFrameRetainsOnlyItsSuffixWithoutGrowth() {
  val b=StandbyAudioBuffer(8000) { 0 };val ticket=b.begin();val input=ShortArray(20000) { it.toShort() }
  b.append(ticket,input,input.size);input.fill(0)
  assertEquals(16000,b.count());assertEquals(4000.toShort(),b.sample(0));assertEquals(19999.toShort(),b.sample(15999))
 }
 @Test fun idleExpiryAndClockRegressionClearInsteadOfKeepingOldAudio() {
  var time=100L;val b=StandbyAudioBuffer(8000) { time };val ticket=b.begin();b.append(ticket,shortArrayOf(42),1)
  time+=1_999_999_999;assertEquals(1,b.count());time++;b.expire();assertEquals(0,b.count())
  b.append(ticket,shortArrayOf(43),1);time=0;assertEquals(0,b.count())
 }
 @Test fun stopAndOldCallbacksCannotRefillNewCapture() {
  val b=StandbyAudioBuffer(8000) { 0 };val old=b.begin();b.append(old,shortArrayOf(7),1);b.close();b.append(old,shortArrayOf(8),1);assertEquals(0,b.count())
  val fresh=b.begin();b.append(fresh,shortArrayOf(9),1);b.append(old,shortArrayOf(10),1);assertEquals(1,b.count());assertEquals(9.toShort(),b.sample(0))
  b.clear();assertEquals(0,b.count());b.append(fresh,shortArrayOf(11),1);assertEquals(11.toShort(),b.sample(0))
 }
 @Test fun invalidRateAndFrameAreRejectedWithoutRetainingInvalidInput() {
  assertThrows(IllegalArgumentException::class.java) { StandbyAudioBuffer(Int.MAX_VALUE) }
  val b=StandbyAudioBuffer();val ticket=b.begin();assertThrows(IllegalArgumentException::class.java) { b.append(ticket,shortArrayOf(1),2) }
  b.append(ticket,ShortArray(100000) { 2 },100000);b.close();assertEquals(0,b.count())
 }
 @Test fun realCaptureStopClearsRetainedAndReadBuffersWithoutASR() {
  val ring=StandbyAudioBuffer();lateinit var capture:ForegroundCapture;var reads=0;var source:ShortArray?=null
  val device=object:CaptureDevice {
   override fun start() {};override fun close() {}
   override fun read(samples:ShortArray):Int { source=samples;reads++;if(reads==1) { samples.fill(42);return 320 };assertEquals(320,ring.count());capture.releaseCapture();return 0 }
  }
  capture=ForegroundCapture(java.util.concurrent.Executor { it.run() },{true},{device},standby=ring)
  capture.beginCapture({assertTrue(it)},{fail("unexpected capture failure")})
  assertEquals(2,reads);assertEquals(0,ring.count());assertTrue(source!!.all {it==0.toShort()})
 }
}
