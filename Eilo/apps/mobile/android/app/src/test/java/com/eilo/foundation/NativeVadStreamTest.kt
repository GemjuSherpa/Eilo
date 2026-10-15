package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test

class NativeVadStreamTest {
    private class Api : NativeVadApi {
        var opens=0;var calls=0;var closes=0;var next=0
        var onCreate:()->Unit={};var onProcess:()->Unit={};var onClose:()->Unit={}
        var output: ((Int,Boolean)->NativeVadObservation?)?=null
        override fun create(model:String):Long { opens++;onCreate();return 1 }
        override fun process(handle:Long,pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation? {
            calls++;onProcess();val result=output?.invoke(count,final) ?: NativeVadObservation(.9f,next,count,final)
            next+=count;return result
        }
        override fun destroy(handle:Long){closes++;onClose()}
    }
    private fun rejected(block:()->Unit) { try { block();fail("must reject") } catch (_:IllegalStateException) {} catch (_:IllegalArgumentException) {} }
    @Test fun unavailableInvalidPathAndDeniedLeaseNeverOpen() {
        rejected { NativeVadStream("/synthetic",{true}) }
        val api=Api()
        for(path in listOf("relative","/bad\u0000path","/"+"x".repeat(4096))) rejected { NativeVadStream(path,{true},api) }
        rejected { NativeVadStream("/synthetic",{false},api) };assertEquals(0,api.opens)
    }
    @Test fun revocationDuringCreateClosesCandidate() {
        var valid=true;val api=Api();api.onCreate={valid=false}
        rejected { NativeVadStream("/synthetic",{valid},api) };assertEquals(1,api.closes)
    }
    @Test fun revocationDuringInferenceCannotReleaseOrRevive() {
        var valid=true;val api=Api();api.onProcess={valid=false}
        val s=NativeVadStream("/synthetic",{valid},api);val pcm=FloatArray(512)
        rejected { s.process(pcm,512,false) };valid=true;rejected { s.process(pcm,512,false) }
        s.close();assertEquals(1,api.calls);assertEquals(1,api.closes)
    }
    @Test fun invalidInputNeverReachesBackend() {
        for((count,final,value) in listOf(Triple(0,false,0f),Triple(513,true,0f),Triple(7,false,0f),Triple(512,false,Float.NaN),Triple(512,false,1.1f))) {
            val api=Api();val s=NativeVadStream("/synthetic",{true},api)
            rejected { s.process(FloatArray(count){value},count,final) };assertEquals(0,api.calls);assertEquals(1,api.closes)
        }
    }
    @Test fun invalidNativeMetadataAndExceptionsClose() {
        for(frame in listOf(NativeVadObservation(.9f,1,512,false),NativeVadObservation(.9f,0,511,false),NativeVadObservation(.9f,0,512,true),NativeVadObservation(Float.NaN,0,512,false))) {
            val api=Api();api.output={_,_->frame};val s=NativeVadStream("/synthetic",{true},api)
            rejected { s.process(FloatArray(512),512,false) };s.close();assertEquals(1,api.closes)
        }
        val api=Api();api.onProcess={error("native failure")};val s=NativeVadStream("/synthetic",{true},api)
        rejected { s.process(FloatArray(512),512,false) };assertEquals(1,api.closes)
    }
    @Test fun finalClosesOnceAndCallerPcmIsPreserved() {
        val api=Api();val s=NativeVadStream("/synthetic",{true},api);val pcm=FloatArray(512){.25f}
        assertEquals(0,s.process(pcm,512,false).startSample);assertEquals(7,s.process(pcm,7,true).samples)
        assertArrayEquals(FloatArray(512){.25f},pcm,0f);assertEquals(1,api.closes)
        rejected { s.process(pcm,512,false) };s.close();assertEquals(1,api.closes)
    }
    @Test fun revocationDuringFinalCleanupWithholdsFrame() {
        var valid=true;val api=Api();api.onClose={valid=false};val s=NativeVadStream("/synthetic",{valid},api)
        rejected { s.process(FloatArray(7),7,true) };assertEquals(1,api.closes)
    }
    @Test fun thirtySecondLimitCannotReachBackendAgain() {
        val api=Api();val s=NativeVadStream("/synthetic",{true},api);val pcm=FloatArray(512)
        repeat(937){s.process(pcm,512,false)};rejected{s.process(pcm,512,false)}
        assertEquals(937,api.calls);assertEquals(1,api.closes)
    }
}
