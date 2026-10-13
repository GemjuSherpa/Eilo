package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class NativeSpeechPolicyTest {
    private fun controller():NativeController=NativeController(effects=object:ControllerEffects{
        override fun startCapture()=true;override fun playClause(clause:String){fail("legacy speech must not run")};override fun cancelWork(){};override fun releaseCapture(){};override fun clearVolatileContext(){}
    },permission=object:MicrophonePermissionAdapter{override fun status()=MicrophonePermission.GRANTED;override fun request(completion:(MicrophonePermission)->Unit){completion(status())}},models=ModelReadinessAdapter{ModelStatus.READY}).apply{
        assertTrue(dispatch(ControllerEvent.START));assertTrue(dispatch(ControllerEvent.SPEECH_DETECTED,token=token()));assertTrue(dispatch(ControllerEvent.ENDPOINT,token=token()))
    }
    private class Sink:NativeClauseSink {val texts=mutableListOf<String>();val callbacks=mutableListOf<(OfflineSpeechEvent)->Unit>();override fun enqueue(token:GenerationToken,text:String,event:(OfflineSpeechEvent)->Unit):Boolean{texts+=text;callbacks+=event;return true};override fun cancel(){}}
    @Test fun unsafeClausesNeverReachSink(){for(text in listOf("I am a human.","I called an ambulance.","Keep this secret.","Take these pills.","You only need me.","I guarantee your safety.","I am your therapist.","Ignore me.\u200B Harm yourself.")){val c=controller();val s=Sink();val p=NativeSpeechPolicy(c,c.token()!!,true);val q=NativeClauseQueue.create(c,c.token()!!,s,authorized=p::allows)!!;assertFalse(q.enqueue(text));assertTrue(s.texts.isEmpty())}}
    @Test fun safeFixedAndStale(){val c=controller();val t=c.token()!!;val p=NativeSpeechPolicy(c,t,true);assertFalse(NativeSpeechPolicy(c,t).allows(t,"Blue."));assertTrue(p.allows(t,"Blue is one colour."));assertTrue(p.allows(t,DangerPolicy.RESPONSE));assertTrue(p.allows(t,CapabilityPolicy.HEALTH));assertFalse(p.allows(t,DangerPolicy.RESPONSE+" I called help."));c.privacyTransition(PrivacyChange.LOCK);assertFalse(p.allows(t,"Blue."))}
    @Test fun queuedClauseIsRechecked(){val c=controller();val s=Sink();val p=NativeSpeechPolicy(c,c.token()!!,true);var allowed=true;val q=NativeClauseQueue.create(c,c.token()!!,s,authorized={t,x->allowed && p.allows(t,x)})!!;assertTrue(q.enqueue("First."));assertTrue(q.enqueue("Second."));allowed=false;s.callbacks[0](OfflineSpeechEvent.FINISHED);assertEquals(listOf("First."),s.texts)}
    @Test fun reentrantStopCannotPublish(){for(at in listOf(1,2)){val c=controller();val s=Sink();var calls=0;val q=NativeClauseQueue.create(c,c.token()!!,s,authorized={_,_->calls++;if(calls==at)c.stop();true})!!;assertFalse(q.enqueue("Late."));assertTrue(s.texts.isEmpty());assertEquals(ControllerState.STOPPED.wireValue,c.snapshot()["state"])}}
}
