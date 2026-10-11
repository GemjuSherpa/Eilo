package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class RecognitionPolicyTest {
    @Test fun uncertainAmbiguousOverlapNeverReachConversationOrFactProcessing(){
        for ((score,ambiguous,overlap) in listOf(Triple(null,false,false),Triple(.3f,false,false),Triple(.95f,true,false),Triple(.95f,false,true),Triple(Float.NaN,false,false))){
            val spoken=mutableListOf<String>();val c=testController(effects=object:ControllerEffects{override fun startCapture()=true;override fun playClause(clause:String){spoken.add(clause)};override fun cancelWork(){};override fun releaseCapture(){};override fun clearVolatileContext(){}})
            c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());val t=c.token()!!;var accepted=0
            assertTrue(c.finishRecognition(t,AsrText("My name is Jemju Shurpa",true),score,ambiguous,overlap,{true},{accepted++}))
            assertEquals(listOf(RecognitionPolicy.CLARIFICATION),spoken);assertEquals(0,accepted)
            assertFalse(c.finishRecognition(t,AsrText("duplicate",true),.95f,active={true},accepted={fail()}))
        }
    }
    @Test fun partialStaleOrRevokedFinalCannotSpeakOrQueue(){val c=testController();c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());val t=c.token()!!
        assertFalse(c.finishRecognition(t,AsrText("question",false),.95f,active={true},accepted={fail()}))
        assertFalse(c.finishRecognition(t,AsrText("question",true),.95f,active={false},accepted={fail()}));c.stop()
        assertFalse(c.finishRecognition(t,AsrText("question",true),.95f,active={true},accepted={fail()}))
    }
    @Test fun clearFinalIsQueuedOnceWithoutPersisting(){val c=testController();c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());val received=mutableListOf<String>();val t=c.token()!!
        assertTrue(c.finishRecognition(t,AsrText("  what time is it  ",true),.95f,active={true},accepted={received.add(it)}));assertEquals(listOf("what time is it"),received);assertEquals(ControllerState.THINKING,c.state())
    }
}
