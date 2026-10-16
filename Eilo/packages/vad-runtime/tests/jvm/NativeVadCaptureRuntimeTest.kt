package com.eilo.foundation

import java.io.File
import java.security.MessageDigest
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import org.junit.Assert.*
import org.junit.Test

/** Opt-in actual JNI transport execution on macOS JVM, not Android ART or microphone capture. */
class NativeVadCaptureRuntimeTest {
    private fun sha(path:String)=MessageDigest.getInstance("SHA-256").digest(File(path).readBytes()).joinToString(""){"%02x".format(it)}
    @Test fun actualModelOnSeparateCaptureTransportWorker() {
        val model=System.getProperty("eilo.vad.model");val runtime=System.getProperty("eilo.vad.runtime");val wrapper=System.getProperty("eilo.vad.wrapper")
        val base=NativeVadJni.loadVerified(listOf(runtime,wrapper)) {
            sha(model)=="6b99cbfd39246b6706f98ec13c7c50c6b299181f2474fa05cbc8046acc274396" &&
                sha(runtime)==System.getProperty("eilo.vad.runtimeSha") && sha(wrapper)==System.getProperty("eilo.vad.wrapperSha")
        }
        val worker=Executors.newSingleThreadExecutor { r->Thread(r,"actual-vad-capture") }
        var valid=true;var revokeOnClose=false;var stopDuring=false;var stop:()->Unit={}
        var opens=0;var closes=0;var calls=0;var failures=0
        val events=mutableListOf<VadCaptureOutcome>();var asrOpens=0;var ownedAudio:VadAsrHandoff?=null
        val controller=testController();assertTrue(controller.dispatch(ControllerEvent.START));val token=controller.token()!!
        val api=object:NativeVadApi {
            override fun create(model:String):Long {
                assertEquals("actual-vad-capture",Thread.currentThread().name)
                val h=base.create(model);if(h>0)opens++;return h
            }
            override fun process(handle:Long,pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation? {
                assertEquals("actual-vad-capture",Thread.currentThread().name);calls++
                val frame=base.process(handle,pcm,count,final);if(stopDuring)stop();return frame
            }
            override fun destroy(handle:Long) {
                assertEquals("actual-vad-capture",Thread.currentThread().name);closes++;base.destroy(handle);if(revokeOnClose)valid=false
            }
        }
        fun barrier(){worker.submit{}.get(20,TimeUnit.SECONDS)}
        fun transport(withAudio:Boolean=false,rate:Int=16000):VadCaptureTransport {
            val factory:(()->VadAsrHandoff)?=if(!withAudio)null else { {VadAsrHandoff(token,{valid},{asrOpens++;error("quiet ASR must not open")}).also{ownedAudio=it}} }
            return VadCaptureTransport(worker,{valid},{NativeVadStream(model,{valid},api)},failure={active->assertTrue(active());failures++},output={e,active->assertTrue(active());events.add(e)},audioFactory=factory,sourceRate=rate)
        }
        fun feed(d:VadCaptureTransport,count:Int=320,rate:Int=16000){assertTrue(d.submit(ShortArray(count),count,rate));barrier()}
        val owned=mutableListOf<VadCaptureTransport>()
        fun owned(withAudio:Boolean=false,rate:Int=16000)=transport(withAudio,rate).also{owned.add(it)}
        try {
            val quiet=owned(true);repeat(250){feed(quiet)}
            assertEquals(VadCaptureOutcome(EndpointResult.NO_SPEECH,80000,320),events.single());assertEquals(0,quiet.retainedSamples());assertEquals(0,asrOpens);assertEquals(0,ownedAudio?.retainedSamples());quiet.close();barrier()
            val eof=owned();feed(eof,7);eof.finish();barrier()
            assertEquals(2,events.size);assertEquals(VadCaptureOutcome(EndpointResult.INCOMPLETE,7,0),events[1]);eof.close();barrier()
            val revoked=owned();stop={revoked.close()};stopDuring=true;feed(revoked,512)
            assertEquals(2,events.size);assertEquals(0,failures);assertFalse(revoked.current());stopDuring=false;stop={}
            val idle=owned();feed(idle,512);val before=closes;idle.close();barrier()
            assertEquals(before+1,closes);assertFalse(idle.current());assertEquals(0,idle.retainedSamples())
            val cleanup=owned();feed(cleanup,7);revokeOnClose=true;cleanup.finish();barrier()
            assertEquals(2,events.size);assertEquals(1,failures);assertFalse(cleanup.current());revokeOnClose=false;valid=true
            assertEquals(5,opens);assertEquals(5,closes);assertEquals(161,calls)
            val wide=owned(true,48000);repeat(500){feed(wide,480,48000)}
            assertEquals(3,events.size);assertEquals(EndpointResult.NO_SPEECH,events[2].result);assertEquals(80000,events[2].totalSamples)
            assertEquals(0,asrOpens);assertEquals(0,ownedAudio?.retainedSamples());assertEquals(0,wide.retainedSamples())
            wide.close();barrier();assertEquals(6,opens);assertEquals(6,closes);assertEquals(318,calls)
            File(System.getProperty("eilo.vad.result")).writeText("""{"scope":"MACOS_JVM_JNI_CAPTURE_TRANSPORT","synthetic":true,"quiet_valid_samples":80000,"eof_valid_samples":7,"native_calls":318,"opens":6,"closes":6,"wide_source_samples":240000,"wide_normalized_samples":80000,"separate_worker_verified":true,"quiet_asr_opens":0,"quiet_owned_audio_cleared":true,"stop_during_inference_rejected":true,"stop_without_new_frames_closed":true,"cleanup_revocation_rejected":true,"physical":"NOT_RUN"}"""+"\n")
        } finally {owned.forEach{it.close()};barrier();worker.shutdown();assertTrue(worker.awaitTermination(20,TimeUnit.SECONDS))}
    }
}
