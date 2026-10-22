package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class GenericSpokenTurnTest {
    private fun controller():NativeController=NativeController(effects=object:ControllerEffects{
        override fun startCapture()=true;override fun playClause(clause:String){fail("legacy speech must not run")};override fun cancelWork(){};override fun releaseCapture(){};override fun clearVolatileContext(){}
    },permission=object:MicrophonePermissionAdapter{override fun status()=MicrophonePermission.GRANTED;override fun request(completion:(MicrophonePermission)->Unit){completion(status())}},models=ModelReadinessAdapter{ModelStatus.READY}).apply{
        assertTrue(dispatch(ControllerEvent.START));assertTrue(dispatch(ControllerEvent.SPEECH_DETECTED,token=token()))
    }

    private class Sink:NativeClauseSink {val texts=mutableListOf<String>();val callbacks=mutableListOf<(OfflineSpeechEvent)->Unit>();override fun enqueue(token:GenerationToken,text:String,event:(OfflineSpeechEvent)->Unit):Boolean{texts+=text;callbacks+=event;return true};override fun cancel(){}}
    @Test fun finalOnceThroughGenerationAndSpeech(){val c=controller();val s=Sink();var starts=0;val turn=GenericSpokenTurn(c,c.token()!!,s,true,GenericReplyStarter{_,request,consume,finish->starts++;assertEquals("Name one colour.",request.latest);val bytes="Blue is one colour.".toByteArray();consume(bytes,bytes.size);finish(LlmJobResult.COMPLETED);true});assertFalse(turn.submit(AsrText("Draft",false),1f));assertTrue(turn.submit(AsrText("Name one colour.",true),0.95f));assertFalse(turn.submit(AsrText("Duplicate",true),1f));assertEquals(1,starts);assertEquals(listOf("Blue is one colour."),s.texts);s.callbacks[0](OfflineSpeechEvent.STARTED);s.callbacks[0](OfflineSpeechEvent.FINISHED);assertEquals(ControllerState.STANDBY,c.state())}
    @Test fun fixedRepliesNeverStartModel(){for(item in listOf(Triple("Name one colour.",null,RecognitionPolicy.CLARIFICATION),Triple("I will kill myself now.",0.95f,DangerPolicy.RESPONSE),Triple("Take a photo.",0.95f,CapabilityPolicy.ACTION))){val c=controller();val s=Sink();val turn=GenericSpokenTurn(c,c.token()!!,s,true,GenericReplyStarter{_,_,_,_->fail("fixed routing must not generate");false});assertTrue(turn.submit(AsrText(item.first,true),item.second));assertEquals(listOf(item.third),s.texts)}}
    @Test fun defaultDeniedAndUnavailable(){val c=controller();val s=Sink();assertFalse(GenericSpokenTurn(c,c.token()!!,s).submit(AsrText("Hello",true),1f));assertFalse(GenericSpokenTurn(c,c.token()!!,s,true).submit(AsrText("Hello",true),1f));assertEquals(ControllerState.ERROR,c.state());assertTrue(s.texts.isEmpty())}
    @Test fun lateOutputCannotSpeak(){val c=controller();val s=Sink();var receive:((ByteArray,Int)->Unit)?=null;var finish:((LlmJobResult)->Unit)?=null;val turn=GenericSpokenTurn(c,c.token()!!,s,true,GenericReplyStarter{_,_,r,f->receive=r;finish=f;true});assertTrue(turn.submit(AsrText("Hello",true),1f));c.stop();try{val b="Late.".toByteArray();receive!!(b,b.size);fail("stale accepted")}catch(_:IllegalStateException){};finish!!(LlmJobResult.COMPLETED);assertTrue(s.texts.isEmpty());assertEquals(ControllerState.STOPPED,c.state())}
    @Test fun throwingStarterFailsClosedAndClearsBorrowedRequest(){
        val c=controller();val s=Sink();var request:GenericReplyRequest?=null
        val turn=GenericSpokenTurn(c,c.token()!!,s,true,GenericReplyStarter{_,r,_,_->request=r;throw IllegalStateException("private adapter detail")})
        assertFalse(turn.submit(AsrText("Name one colour.",true),0.95f))
        assertEquals(ControllerState.ERROR,c.state());assertTrue(s.texts.isEmpty())
        assertEquals("",request!!.latest);assertTrue(request!!.history.isEmpty())
    }
    @Test fun rejectedStarterClearsRetainedRequestAndRejectsLateCallbacks(){
        val c=controller();val s=Sink();var request:GenericReplyRequest?=null
        var receive:((ByteArray,Int)->Unit)?=null;var finish:((LlmJobResult)->Unit)?=null
        val turn=GenericSpokenTurn(c,c.token()!!,s,true,GenericReplyStarter{_,r,p,f->request=r;receive=p;finish=f;false})
        assertFalse(turn.submit(AsrText("Name one colour.",true),0.95f))
        assertEquals("",request!!.latest);assertTrue(request!!.history.isEmpty())
        try{val bytes="Late answer.".toByteArray();receive!!(bytes,bytes.size);fail("late accepted")}catch(_:IllegalStateException){}
        finish!!(LlmJobResult.COMPLETED);assertTrue(s.texts.isEmpty());assertEquals(ControllerState.ERROR,c.state())
    }

    @Test fun stopClearsRequestBeforeAdapterCompletion(){
        val c=controller();val s=Sink();var request:GenericReplyRequest?=null;var finish:((LlmJobResult)->Unit)?=null
        val turn=GenericSpokenTurn(c,c.token()!!,s,true,GenericReplyStarter{_,r,_,f->request=r;finish=f;true})
        assertTrue(turn.submit(AsrText("Name one colour.",true),0.95f));assertEquals("Name one colour.",request!!.latest)
        c.stop();assertEquals("",request!!.latest);assertTrue(request!!.history.isEmpty())
        finish!!(LlmJobResult.COMPLETED);assertEquals(ControllerState.STOPPED,c.state());assertTrue(s.texts.isEmpty())
    }
    @Test fun normalCompletionClearsRequestAndRetainsSuccessfulReply(){
        val c=controller();val s=Sink();var request:GenericReplyRequest?=null
        val turn=GenericSpokenTurn(c,c.token()!!,s,true,GenericReplyStarter{_,r,p,f->request=r;val bytes="Blue is one colour.".toByteArray();p(bytes,bytes.size);f(LlmJobResult.COMPLETED);true})
        assertTrue(turn.submit(AsrText("Name one colour.",true),0.95f));assertEquals("",request!!.latest)
        assertEquals(listOf("Blue is one colour."),s.texts);s.callbacks[0](OfflineSpeechEvent.STARTED);s.callbacks[0](OfflineSpeechEvent.FINISHED)
        assertEquals(ControllerState.STANDBY,c.state())
    }
    @Test fun stopThenThrowCannotRestoreErrorOrOutput(){
        val c=controller();val s=Sink();var request:GenericReplyRequest?=null
        val turn=GenericSpokenTurn(c,c.token()!!,s,true,GenericReplyStarter{_,r,_,_->request=r;c.stop();throw IllegalStateException("private detail")})
        assertFalse(turn.submit(AsrText("Name one colour.",true),0.95f));assertEquals("",request!!.latest)
        assertEquals(ControllerState.STOPPED,c.state());assertTrue(s.texts.isEmpty())
    }

}
