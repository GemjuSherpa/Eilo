package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class NativeClauseQueueTest {
    private class Sink: NativeClauseSink {
        val texts=ArrayList<String>();val callbacks=ArrayList<(OfflineSpeechEvent)->Unit>();var stops=0;var ok=true
        override fun enqueue(token:GenerationToken,text:String,event:(OfflineSpeechEvent)->Unit):Boolean {texts.add(text);callbacks.add(event);return ok}
        override fun cancel(){stops++}
    }
    private fun controller():NativeController=NativeController(effects=object:ControllerEffects{
        override fun startCapture()=true;override fun playClause(clause:String){fail("legacy speech must not run")};override fun cancelWork(){};override fun releaseCapture(){};override fun clearVolatileContext(){}
    },permission=object:MicrophonePermissionAdapter{override fun status()=MicrophonePermission.GRANTED;override fun request(completion:(MicrophonePermission)->Unit){completion(status())}},models=ModelReadinessAdapter{ModelStatus.READY}).apply{
        assertTrue(dispatch(ControllerEvent.START));assertTrue(dispatch(ControllerEvent.SPEECH_DETECTED,token=token()));assertTrue(dispatch(ControllerEvent.ENDPOINT,token=token()))
    }
    @Test fun orderGapAndSealOnlyEndAfterLastClause(){val c=controller();val t=c.token()!!;val s=Sink();val q=NativeClauseQueue.create(c,t,s){_,_->true}!!
        assertTrue(q.enqueue("First."));assertTrue(q.enqueue("Second."));assertTrue(q.seal());assertEquals(listOf("First."),s.texts)
        s.callbacks[0](OfflineSpeechEvent.STARTED);assertEquals(ControllerState.SPEAKING.wireValue,c.snapshot()["state"])
        s.callbacks[0](OfflineSpeechEvent.FINISHED);assertSame(t,c.token());assertEquals(listOf("First.","Second."),s.texts)
        s.callbacks[0](OfflineSpeechEvent.FINISHED);assertSame(t,c.token())
        s.callbacks[1](OfflineSpeechEvent.STARTED);s.callbacks[1](OfflineSpeechEvent.FINISHED);assertEquals(ControllerState.STANDBY.wireValue,c.snapshot()["state"]);assertTrue(t.cancelled)
    }
    @Test fun stopClearsAndLateCallbackCannotStartNext(){val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!
        assertTrue(q.enqueue("First."));assertTrue(q.enqueue("Second."));c.stop();s.callbacks[0](OfflineSpeechEvent.FINISHED);assertEquals(listOf("First."),s.texts);assertTrue(s.stops>0);assertFalse(q.enqueue("Late."));assertEquals(ControllerState.STOPPED.wireValue,c.snapshot()["state"])
    }
    @Test fun overflowAndDefaultDeniedFailClosed(){for(default in listOf(false,true)){val c=controller();val s=Sink();val q=if(default)NativeClauseQueue.create(c,c.token()!!,s)!! else NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!
        if(default){assertFalse(q.enqueue("Denied."));assertTrue(s.texts.isEmpty())}else{repeat(5){assertTrue(q.enqueue("Clause."))};assertFalse(q.enqueue("Overflow."));assertEquals(1,s.texts.size)};assertTrue(s.stops>0);assertEquals(ControllerState.ERROR.wireValue,c.snapshot()["state"])
    }}
    @Test fun recheckAuthorizationBeforeDrainAndSinkFailure(){val c=controller();val s=Sink();var allowed=true;val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->allowed}!!
        assertTrue(q.enqueue("First."));assertTrue(q.enqueue("Second."));allowed=false;s.callbacks[0](OfflineSpeechEvent.FINISHED);assertEquals(1,s.texts.size);assertEquals(ControllerState.ERROR.wireValue,c.snapshot()["state"])
        val c2=controller();val bad=Sink().apply{ok=false};val q2=NativeClauseQueue.create(c2,c2.token()!!,bad){_,_->true}!!;assertFalse(q2.enqueue("Failure."));assertEquals(ControllerState.ERROR.wireValue,c2.snapshot()["state"])
    }
    @Test fun llmRemainsAllowedDuringPlaybackAndGap(){val c=controller();val t=c.token()!!;val llm=c.prepareLlmWork(t){true}!!;val s=Sink();val q=NativeClauseQueue.create(c,t,s){_,_->true}!!
        assertTrue(q.enqueue("First."));s.callbacks[0](OfflineSpeechEvent.STARTED);assertTrue(c.llmWorkAllowed(llm));s.callbacks[0](OfflineSpeechEvent.FINISHED);assertEquals(ControllerState.THINKING.wireValue,c.snapshot()["state"]);assertTrue(c.llmWorkAllowed(llm));q.cancel();assertFalse(c.llmWorkAllowed(llm))
    }
    @Test fun fragmentedNaturalClausesAndOversizeAreBounded(){val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!
        assertTrue(q.append("Value 1."));assertTrue(q.append("5 is fine. Next"));assertEquals(listOf("Value 1.5 is fine."),s.texts);assertTrue(q.append(" clause!"));assertTrue(q.seal());s.callbacks[0](OfflineSpeechEvent.FINISHED);assertEquals(listOf("Value 1.5 is fine.","Next clause!"),s.texts)
        val c2=controller();val s2=Sink();val q2=NativeClauseQueue.create(c2,c2.token()!!,s2){_,_->true}!!;assertTrue(q2.append("x".repeat(1024)));assertFalse(q2.append("y"));assertTrue(s2.texts.isEmpty())
    }

}
