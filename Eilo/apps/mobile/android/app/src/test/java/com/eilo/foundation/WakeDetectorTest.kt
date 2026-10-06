package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test

private class KeywordFixture : WakeKeywordStream {
    var result="";var pending=2;var accepted=0;var decoded=0;var resets=0;var closed=0
    var onAccept:(()->Unit)?=null
    var fail="";var endless=false;var borrowed:FloatArray?=null
    override fun accept(samples:FloatArray,count:Int,sampleRate:Int) {
        accepted++;borrowed=samples;onAccept?.invoke()
        assertEquals(16000,sampleRate);assertEquals(4,count)
        assertEquals(listOf(-1f,-0.5f,0f,32767f/32768f),samples.take(count))
        if(fail=="accept") error("synthetic")
    }
    override fun ready():Boolean { if(fail=="ready") error("synthetic");return endless || pending>0 }
    override fun decode() { decoded++;pending--;if(fail=="decode") error("synthetic") }
    override fun keyword():String { if(fail=="result") error("synthetic");return result }
    override fun reset() { resets++;result="";if(fail=="reset") error("synthetic") }
    override fun close() { closed++;if(fail=="close") error("synthetic") }
}
class WakeDetectorTest {
    private val config=WakeConfiguration("HEY EILO",0.6f,1.5f)
    private val pcm=shortArrayOf(-32768,-16384,0,32767)
    private fun process(d:WakeDetector,t:GenerationToken)=d.processPCM16(t,pcm,pcm.size,16000)
    @Test fun frozenKeywordResultsGateActivationWithoutConversationalWork() {
        val effects=EffectsSpy();val c=testController(effects=effects);c.dispatch(ControllerEvent.START);val t=c.token()!!
        val engine=KeywordFixture();val d=WakeDetector(config,verified={true},open={ assertEquals(config,it);engine });assertTrue(d.begin(t))
        // Frozen result contract cases, not an acoustic classifier or recognition quality test.
        for(result in listOf("","ordinary speech","HEY OTHER","HEY EILO trailing")) {
            engine.result=result;assertNull(process(d,t));assertEquals(ControllerState.STANDBY,c.state());assertTrue(engine.borrowed!!.all { it==0f })
        }
        engine.result="HEY EILO";val event=process(d,t)!!
        assertEquals(ControllerState.STANDBY,c.state());assertTrue(event.apply(c));assertEquals(ControllerState.CAPTURING,c.state());assertFalse(event.apply(c))
        assertEquals(0,effects.clauses.size);assertTrue(engine.borrowed!!.all { it==0f });assertEquals(4,engine.resets);d.close()
    }
    @Test fun stopAndPrivacyTransitionsRejectQueuedWakeAndCancelledInput() {
        for(privacy in listOf<PrivacyChange?>(null,PrivacyChange.LOCK,PrivacyChange.PRIVATE_SESSION,PrivacyChange.IDENTITY_RESET)) {
            val c=testController();c.dispatch(ControllerEvent.START);val t=c.token()!!;val engine=KeywordFixture();engine.result="HEY EILO"
            val d=WakeDetector(config,verified={true},open={engine});assertTrue(d.begin(t));val event=process(d,t)!!
            if(privacy==null)c.stop() else c.privacyTransition(privacy)
            assertFalse(event.apply(c));assertNull(process(d,t));assertEquals(1,engine.accepted);assertEquals(1,engine.closed)
        }
    }
    @Test fun cancellationDuringDecodeAndRevokedPermissionRejectActivation() {
        val permission=FakePermission();val c=testController(permission=permission);c.dispatch(ControllerEvent.START);val t=c.token()!!;val engine=KeywordFixture();engine.result="HEY EILO"
        val d=WakeDetector(config,verified={true},open={engine});d.begin(t);engine.onAccept={c.stop()};assertNull(process(d,t));assertEquals(1,engine.closed)
        c.dispatch(ControllerEvent.START);val fresh=c.token()!!;engine.onAccept=null;engine.result="HEY EILO";d.begin(fresh);val event=process(d,fresh)!!
        permission.value=MicrophonePermission.DENIED;assertFalse(event.apply(c));assertEquals(ControllerState.STOPPED,c.state());d.close()
    }
    @Test fun closedOrReboundDetectorRejectsQueuedEventEvenWithSameControllerToken() {
        val c=testController();c.dispatch(ControllerEvent.START);val t=c.token()!!;val engine=KeywordFixture();engine.result="HEY EILO"
        val d=WakeDetector(config,verified={true},open={engine});d.begin(t);val event=process(d,t)!!;d.close();assertFalse(event.apply(c))
        engine.result="HEY EILO";d.begin(t);val second=process(d,t)!!;engine.result="HEY EILO";d.begin(t);assertFalse(second.apply(c));assertTrue(process(d,t)!!.apply(c));d.close()
    }
    @Test fun restartClosesOldStreamAndOldTokenCannotPoisonNewStream() {
        val c=testController();c.dispatch(ControllerEvent.START);val old=c.token()!!;val first=KeywordFixture();val second=KeywordFixture();var opens=0
        val d=WakeDetector(config,verified={true},open={ if(opens++==0) first else second });assertTrue(d.begin(old))
        c.stop();c.dispatch(ControllerEvent.START);val fresh=c.token()!!;assertTrue(d.begin(fresh));assertEquals(1,first.closed)
        assertNull(process(d,old));assertEquals(0,second.closed);second.result="HEY EILO";assertTrue(process(d,fresh)!!.apply(c));d.close()
    }
    @Test fun missingVerificationAndRevocationFailClosed() {
        val c=testController();c.dispatch(ControllerEvent.START);val t=c.token()!!;assertFalse(WakeDetector(config).begin(t))
        var verified=false;var opens=0;val engine=KeywordFixture();val d=WakeDetector(config,verified={verified},open={opens++;engine})
        assertFalse(d.begin(t));assertEquals(0,opens);verified=true;assertTrue(d.begin(t));verified=false;assertNull(process(d,t));assertEquals(1,engine.closed)
    }
    @Test fun badInputBoundsCloseBeforeBackendAndPreserveCallerSamples() {
        for(pair in listOf(16000 to 0,16000 to 5,7999 to 4,192001 to 4)) {
            val c=testController();c.dispatch(ControllerEvent.START);val t=c.token()!!;val engine=KeywordFixture();val d=WakeDetector(config,verified={true},open={engine});d.begin(t)
            assertNull(d.processPCM16(t,pcm,pair.second,pair.first));assertEquals(0,engine.accepted);assertEquals(1,engine.closed);assertArrayEquals(shortArrayOf(-32768,-16384,0,32767),pcm)
        }
        val c=testController();c.dispatch(ControllerEvent.START);val t=c.token()!!;val engine=KeywordFixture();val d=WakeDetector(config,verified={true},open={engine});d.begin(t)
        assertNull(d.processPCM16(t,ShortArray(1601),1601,16000));assertEquals(0,engine.accepted)
    }
    @Test fun backendFailuresAndRunawayDecodeEraseAndClose() {
        for(stage in listOf("accept","ready","decode","result","reset","endless")) {
            val c=testController();c.dispatch(ControllerEvent.START);val t=c.token()!!;val engine=KeywordFixture();engine.fail=stage;engine.endless=stage=="endless";engine.result="HEY EILO"
            val d=WakeDetector(config,verified={true},open={engine});d.begin(t);assertNull(process(d,t));assertEquals(1,engine.closed);assertTrue(engine.borrowed!!.all {it==0f});assertTrue(engine.decoded<=32);assertEquals(ControllerState.STANDBY,c.state())
        }
    }
    @Test fun failedReleaseDisablesReopenAndRecordsOnlySafeMetadata() {
        val c=testController();c.dispatch(ControllerEvent.START);val t=c.token()!!;val engine=KeywordFixture();val diagnostics=SafeDiagnostics();var opens=0
        val d=WakeDetector(config,diagnostics,verified={true},open={opens++;engine});d.begin(t);engine.fail="close";d.close();assertFalse(d.begin(t));assertEquals(1,opens)
        assertEquals(listOf(SafeDiagnostic(SafeComponent.MODEL,SafeError.UNAVAILABLE,SafeSeverity.ERROR)),diagnostics.snapshot())
    }
    @Test fun invalidConfigurationAndOpenFailureCannotActivate() {
        for(phrase in listOf("","hey eilo","HEY\nEILO","HEY EILO ","A".repeat(65))) assertThrows(IllegalArgumentException::class.java) { WakeConfiguration(phrase,0.6f,1f) }
        for(threshold in listOf(0f,-1f,Float.NaN,Float.POSITIVE_INFINITY,1.1f)) assertThrows(IllegalArgumentException::class.java) { WakeConfiguration("EILO",threshold,1f) }
        for(boost in listOf(0f,Float.NaN,11f)) assertThrows(IllegalArgumentException::class.java) { WakeConfiguration("EILO",0.6f,boost) }
        val c=testController();c.dispatch(ControllerEvent.START);val d=WakeDetector(config,verified={true});assertFalse(d.begin(c.token()!!))
    }
}
