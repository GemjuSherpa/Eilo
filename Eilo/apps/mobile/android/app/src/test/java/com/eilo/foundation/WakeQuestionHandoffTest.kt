package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class WakeQuestionHandoffTest {
 @Test fun combinedPhraseQuestionHasOneCompleteSuffixAndNoDuplicateFrame() {
  val c=testController();c.dispatch(ControllerEvent.START);val h=WakeQuestionHandoff();val received=mutableListOf<Short>();var calls=0;var borrowed:ShortArray?=null
  assertTrue(h.offer(shortArrayOf(1,2,3,4,5),5,0));assertEquals(0,calls)
  c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());val t=c.token()!!
  assertTrue(h.activate(t,2,{!t.cancelled},{a,n->calls++;borrowed=a;repeat(n){received.add(a[it])}}))
  assertEquals(listOf<Short>(3,4,5),received);assertTrue(borrowed!!.all{it==0.toShort()})
  assertTrue(h.offer(shortArrayOf(4,5,6,7),4,3));assertEquals(listOf<Short>(3,4,5,6,7),received)
  assertTrue(h.offer(shortArrayOf(6,7),2,5));assertEquals(2,calls)
  assertFalse(h.activate(t,null,{true},{_,_->fail()}));h.close()
 }
 @Test fun boundedRetentionAndStopRejectLateHandoff() {
  val c=testController();c.dispatch(ControllerEvent.START);val t=c.token()!!;val h=WakeQuestionHandoff()
  repeat(30){h.offer(ShortArray(1600){1},1600,it*1600L)};assertEquals(32000,h.retainedSamples())
  c.stop();assertFalse(h.activate(t,null,{true},{_,_->fail()}));h.close();assertEquals(0,h.retainedSamples())
 }
 @Test fun gapRevocationAndSinkFailureCloseAndErase() {
  val c=testController();c.dispatch(ControllerEvent.START);val t=c.token()!!
  val gap=WakeQuestionHandoff();gap.offer(shortArrayOf(1),1,0);assertFalse(gap.offer(shortArrayOf(2),1,2));assertEquals(0,gap.retainedSamples())
  for(throws in listOf(false,true)) {
   val h=WakeQuestionHandoff();h.offer(shortArrayOf(1),1,0);var valid=true;var borrowed:ShortArray?=null
   assertFalse(h.activate(t,0,{valid},{a,_->borrowed=a;if(throws)error("synthetic") else valid=false}))
   assertTrue(borrowed!!.all{it==0.toShort()});assertFalse(h.offer(shortArrayOf(2),1,1))
  }
 }
}
