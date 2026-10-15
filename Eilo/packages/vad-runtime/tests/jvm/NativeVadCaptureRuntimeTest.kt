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
        val events=mutableListOf<VadCaptureOutcome>()
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
        fun transport()=VadCaptureTransport(worker,{valid},{NativeVadStream(model,{valid},api)},failure={active->assertTrue(active());failures++},output={e,active->assertTrue(active());events.add(e)})
        fun feed(d:VadCaptureTransport,count:Int=320){assertTrue(d.submit(ShortArray(count),count,16000));barrier()}
        val owned=mutableListOf<VadCaptureTransport>()
        fun owned()=transport().also{owned.add(it)}
        try {
            val quiet=owned();repeat(250){feed(quiet)}
            assertEquals(VadCaptureOutcome(EndpointResult.NO_SPEECH,80000,320),events.single());assertEquals(0,quiet.retainedSamples());quiet.close();barrier()
            val eof=owned();feed(eof,7);eof.finish();barrier()
            assertEquals(2,events.size);assertEquals(VadCaptureOutcome(EndpointResult.INCOMPLETE,7,0),events[1]);eof.close();barrier()
            val revoked=owned();stop={revoked.close()};stopDuring=true;feed(revoked,512)
            assertEquals(2,events.size);assertEquals(0,failures);assertFalse(revoked.current());stopDuring=false;stop={}
            val idle=owned();feed(idle,512);val before=closes;idle.close();barrier()
            assertEquals(before+1,closes);assertFalse(idle.current());assertEquals(0,idle.retainedSamples())
            val cleanup=owned();feed(cleanup,7);revokeOnClose=true;cleanup.finish();barrier()
            assertEquals(2,events.size);assertEquals(1,failures);assertFalse(cleanup.current());revokeOnClose=false;valid=true
            assertEquals(5,opens);assertEquals(5,closes);assertEquals(161,calls)
            File(System.getProperty("eilo.vad.result")).writeText("""{"scope":"MACOS_JVM_JNI_CAPTURE_TRANSPORT","synthetic":true,"quiet_valid_samples":80000,"eof_valid_samples":7,"native_calls":161,"opens":5,"closes":5,"separate_worker_verified":true,"stop_during_inference_rejected":true,"stop_without_new_frames_closed":true,"cleanup_revocation_rejected":true,"physical":"NOT_RUN"}"""+"\n")
        } finally {owned.forEach{it.close()};barrier();worker.shutdown();assertTrue(worker.awaitTermination(20,TimeUnit.SECONDS))}
    }
}
