package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
class NativeClauseQueueTest {
    @Test fun dismissIsVisualOnlySuppressesSameReplyAndRejectsStaleCard(){
        val c=controller();val s=Sink();val token=c.token()!!;val q=NativeClauseQueue.create(c,token,s){_,_->true}!!
        q.enqueue("First.");q.enqueue("Second.");q.seal();s.callbacks[0](OfflineSpeechEvent.FINISHED)
        val shown=c.spokenPresentation(true);val session=shown["sessionId"] as String;val epoch=shown["privacyEpoch"] as Long;val card=shown["cardId"] as String
        assertFalse(c.dismissSpokenPresentation(session,epoch,card,true));assertTrue(c.dismissSpokenPresentation(session,epoch,card))
        assertSame(token,c.token());assertFalse(token.cancelled);assertEquals(0,s.stops)
        c.setSpokenPresentationEnabled(false);c.setSpokenPresentationEnabled(true);s.callbacks[1](OfflineSpeechEvent.FINISHED)
        assertEquals(ControllerState.STANDBY,c.state());assertEquals(emptyList<String>(),c.spokenPresentation(true)["clauses"])
        c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());c.dispatch(ControllerEvent.ENDPOINT,token=c.token())
        val sink=Sink();val next=NativeClauseQueue.create(c,c.token()!!,sink){_,_->true}!!;next.enqueue("New.");sink.callbacks[0](OfflineSpeechEvent.FINISHED)
        assertFalse(c.dismissSpokenPresentation(session,epoch,card));assertEquals(listOf("New."),c.spokenPresentation(true)["clauses"])
    }
    @Test fun idleDismissReleasesCompletedCardWithoutStoppingStandby(){
        val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!;q.enqueue("Done.");q.seal();s.callbacks[0](OfflineSpeechEvent.FINISHED)
        val v=c.spokenPresentation(true);val token=c.token()
        assertTrue(c.dismissSpokenPresentation(v["sessionId"] as String,v["privacyEpoch"] as Long,v["cardId"] as String,true))
        assertSame(token,c.token());assertEquals(ControllerState.STANDBY,c.state());assertEquals(emptyList<String>(),c.spokenPresentation(true)["clauses"])
    }
    @Test fun cardIdentitySurvivesNormalEndAndChangesForNewQuery(){
        val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!
        assertEquals("",c.spokenPresentation(true)["cardId"]);q.enqueue("First.");q.enqueue("Second.");q.seal();s.callbacks[0](OfflineSpeechEvent.FINISHED)
        val first=c.spokenPresentation(true)["cardId"] as String;assertNotNull(java.util.UUID.fromString(first))
        s.callbacks[1](OfflineSpeechEvent.FINISHED);assertEquals(first,c.spokenPresentation(true)["cardId"])
        c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token());assertEquals("",c.spokenPresentation(true)["cardId"])
        c.dispatch(ControllerEvent.ENDPOINT,token=c.token());val next=Sink();val q2=NativeClauseQueue.create(c,c.token()!!,next){_,_->true}!!
        q2.enqueue("New answer.");next.callbacks[0](OfflineSpeechEvent.FINISHED);assertNotEquals(first,c.spokenPresentation(true)["cardId"])
    }
    @Test fun sdkInterruptionLabelsOnlyAnEmptyView(){
        val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!
        q.enqueue("Unfinished words.");s.callbacks[0](OfflineSpeechEvent.STARTED);s.callbacks[0](OfflineSpeechEvent.INTERRUPTED)
        assertEquals(true,c.spokenPresentation(true)["interrupted"]);assertEquals(emptyList<String>(),c.spokenPresentation(true)["clauses"])
        c.stop();assertTrue(c.spokenPresentation(true).isEmpty())
    }
    @Test fun disabledPresentationCannotAccumulateOrResurrectText(){
        val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!
        c.setSpokenPresentationEnabled(false);q.enqueue("Hidden synthetic text.");s.callbacks[0](OfflineSpeechEvent.FINISHED)
        c.setSpokenPresentationEnabled(true);assertEquals(emptyList<String>(),c.spokenPresentation(true)["clauses"])
        q.enqueue("Visible completed text.");s.callbacks[1](OfflineSpeechEvent.FINISHED);assertEquals(listOf("Visible completed text."),c.spokenPresentation(true)["clauses"])
        c.setSpokenPresentationEnabled(false);c.setSpokenPresentationEnabled(true);assertEquals(emptyList<String>(),c.spokenPresentation(true)["clauses"])
    }
    @Test fun presentationContainsOnlyCompletedClausesAndSurvivesTurnEnd(){
        val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!
        q.enqueue("Completed.");q.enqueue("Not finished.");q.seal();s.callbacks[0](OfflineSpeechEvent.STARTED)
        assertEquals(emptyList<String>(),c.spokenPresentation(true)["clauses"])
        s.callbacks[0](OfflineSpeechEvent.FINISHED);assertEquals(listOf("Completed."),c.spokenPresentation(true)["clauses"])
        assertTrue(c.spokenPresentation(false).isEmpty());assertFalse(c.snapshot().containsKey("clauses"))
        s.callbacks[1](OfflineSpeechEvent.FINISHED);assertEquals(listOf("Completed.","Not finished."),c.spokenPresentation(true)["clauses"])
        assertTrue(c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token()));assertEquals(emptyList<String>(),c.spokenPresentation(true)["clauses"])
    }
    @Test fun presentationStopLockPreferenceClearAndLateCallback(){
        for(locked in listOf(false,true)){
            val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!
            q.enqueue("Completed.");s.callbacks[0](OfflineSpeechEvent.FINISHED);c.clearSpokenPresentation();assertEquals(emptyList<String>(),c.spokenPresentation(true)["clauses"])
            q.enqueue("Never completed.");if(locked)c.privacyTransition(PrivacyChange.LOCK) else c.stop();s.callbacks.last()(OfflineSpeechEvent.FINISHED)
            assertTrue(c.spokenPresentation(true).isEmpty())
        }
    }
    @Test fun presentationBoundsAndCancellationCannotReleasePartialClause(){
        val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!
        repeat(8){q.enqueue("x".repeat(900));s.callbacks[it](OfflineSpeechEvent.FINISHED)}
        val shown=c.spokenPresentation(true)
        @Suppress("UNCHECKED_CAST") val clauses=shown["clauses"] as List<String>
        assertTrue(clauses.sumOf{it.toByteArray().size}<=4096);assertEquals(true,shown["earlierClausesOmitted"])
        q.enqueue("Unfinished private suffix.");s.callbacks.last()(OfflineSpeechEvent.STARTED);q.cancel();s.callbacks.last()(OfflineSpeechEvent.FINISHED)
        assertEquals(emptyList<String>(),c.spokenPresentation(true)["clauses"]);assertEquals(true,c.spokenPresentation(true)["interrupted"])
    }
    private class Sink: NativeClauseSink {
        val texts=ArrayList<String>();val callbacks=ArrayList<(OfflineSpeechEvent)->Unit>();var stops=0;var ok=true
        override fun enqueue(token:GenerationToken,text:String,event:(OfflineSpeechEvent)->Unit):Boolean {texts.add(text);callbacks.add(event);return ok}
        override fun cancel(){stops++}
    }
    private fun controller():NativeController=NativeController(effects=object:ControllerEffects{
        override fun startCapture()=true;override fun playClause(clause:String){fail("legacy speech must not run")};override fun cancelWork(){};override fun releaseCapture(){};override fun clearVolatileContext(){}
    },permission=object:MicrophonePermissionAdapter{override fun status()=MicrophonePermission.GRANTED;override fun request(completion:(MicrophonePermission)->Unit){completion(status())}},models=ModelReadinessAdapter{ModelStatus.READY}).apply{
        assertTrue(dispatch(ControllerEvent.START));assertTrue(dispatch(ControllerEvent.SPEECH_DETECTED,token=token()));assertTrue(dispatch(ControllerEvent.ENDPOINT,token=token()));setSpokenPresentationEnabled(true)
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

    @Test fun progressDistinguishesStopRequestFromSdkCompletion(){val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!
        q.enqueue("First.");q.enqueue("Second.");s.callbacks[0](OfflineSpeechEvent.STARTED);assertTrue(q.progress().isEmpty());c.stop();val records=q.progress{true};assertEquals(2,records.size);assertTrue(records[0].sdkStarted);assertTrue(records[0].interruptionRequested);assertFalse(records[0].sdkFinished);assertFalse(records[0].sdkInterrupted);assertTrue(records[1].discardedBeforeStart)
        s.callbacks[0](OfflineSpeechEvent.FINISHED);assertEquals(records,q.progress{true});c.privacyTransition(PrivacyChange.LOCK);assertTrue(q.progress{true}.isEmpty())
    }
    @Test fun sdkCompletionAndInterruptionAreSeparate(){for(event in listOf(OfflineSpeechEvent.FINISHED,OfflineSpeechEvent.INTERRUPTED)){val c=controller();val s=Sink();val q=NativeClauseQueue.create(c,c.token()!!,s){_,_->true}!!;q.enqueue("First.");s.callbacks[0](OfflineSpeechEvent.STARTED);s.callbacks[0](event);val record=q.progress{true}.single();assertEquals(event==OfflineSpeechEvent.FINISHED,record.sdkFinished);assertEquals(event==OfflineSpeechEvent.INTERRUPTED,record.sdkInterrupted)} }
    @Test fun progressLedgerIsBoundedAndContainsNoContent(){val ledger=PlaybackLedger();repeat(40){ledger.produced(java.util.UUID.randomUUID())};assertEquals(32,ledger.snapshot().size);assertTrue(ledger.snapshot().all{it.produced && it.queued});ledger.clear();assertTrue(ledger.snapshot().isEmpty())}

    @Test fun missingSdkCompletionTimesOutAndLateCallbacksCannotDrain(){val c=controller();val s=Sink();var fire:()->Unit={};val scheduler=IdleScheduler{delay,task->assertEquals(60000L,delay);fire=task;IdleCancellation{}};val q=NativeClauseQueue.create(c,c.token()!!,s,scheduler){_,_->true}!!;q.enqueue("First.");q.enqueue("Second.");fire();s.callbacks[0](OfflineSpeechEvent.FINISHED);assertEquals(listOf("First."),s.texts);assertTrue(s.stops>0);assertEquals("error",c.snapshot()["state"]);assertTrue(q.progress{true}.first().failed)}

    @Test fun speechReceiverPublishesBeforeCancellationAndRechecksStop(){val c=controller();var published=false;var cancelled=false;assertNotNull(c.prepareSpeechWork(c.token()!!,{assertTrue(published);cancelled=true},{published=true}));c.stop();assertTrue(cancelled)
        val stopped=controller();val token=stopped.token()!!;assertNull(stopped.prepareSpeechWork(token,{}, {stopped.stop()}));assertTrue(token.cancelled)
    }

}
