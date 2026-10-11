package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test

class StreamingAsrTest {
    private class Backend : AsrStream {
        var calls=0;var closes=0;var result="what time is it";var borrow:FloatArray?=null;var during:()->Unit={}
        override fun accept(pcm:FloatArray,count:Int){calls++;borrow=pcm;assertEquals(.5f,pcm[0],0f)}
        override fun text(finish:Boolean):String{during();return result}
        override fun close(){closes++}
    }
    @Test fun onlyActivationOpensAndScratchIsWipedFinalClosesOnce(){
        val c=testController();c.dispatch(ControllerEvent.START);var opened=0;val b=Backend()
        val t=c.token()!!;var active=false;val a=StreamingAsr(t,{active},{opened++;b})
        assertEquals(0,opened);active=true;assertTrue(a.accept(shortArrayOf(16384),1));assertEquals(1,opened)
        assertTrue(b.borrow!!.all{it==0f});assertEquals("what time is it",a.poll()!!.text)
        assertTrue(a.poll(true)!!.final);assertNull(a.poll(true));a.close();assertEquals(1,b.closes)
    }
    @Test fun stopDuringFinalAndReplacementCannotReleaseText(){
        val c=testController();c.dispatch(ControllerEvent.START);val b=Backend();val a=StreamingAsr(c.token()!!,{true},{b})
        a.accept(shortArrayOf(16384),1);b.during={c.stop();c.dispatch(ControllerEvent.START)}
        assertNull(a.poll(true));assertEquals(1,b.closes)
    }
    @Test fun revokedAndOversizedOutputAndAudioBoundFailClosed(){
        for (bad in listOf("x".repeat(4097),"bad\u0000text")){
            val c=testController();c.dispatch(ControllerEvent.START);val b=Backend();b.result=bad
            val a=StreamingAsr(c.token()!!,{true},{b});a.accept(shortArrayOf(16384),1);assertNull(a.poll());assertEquals(1,b.closes)
        }
        val c=testController();c.dispatch(ControllerEvent.START);val b=Backend();val a=StreamingAsr(c.token()!!,{true},{b})
        repeat(300){assertTrue(a.accept(ShortArray(1600){16384},1600))};assertFalse(a.accept(shortArrayOf(16384),1));assertEquals(1,b.closes)
        var opened=0;val denied=StreamingAsr(c.token()!!,{false},{opened++;b});assertFalse(denied.accept(shortArrayOf(16384),1));assertEquals(0,opened)
    }
}
