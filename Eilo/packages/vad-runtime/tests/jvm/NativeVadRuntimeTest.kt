package com.eilo.foundation

import java.io.File
import java.security.MessageDigest
import org.junit.Assert.*
import org.junit.Test

/** Explicit opt-in host JVM/JNI execution, not an Android/physical target. No microphone. */
class NativeVadRuntimeTest {
    private fun sha(path:String)=MessageDigest.getInstance("SHA-256").digest(File(path).readBytes()).joinToString(""){"%02x".format(it)}
    @Test fun actualWorkerAndOpaqueJniLifetimes() {
        val model=System.getProperty("eilo.vad.model")
        val runtime=System.getProperty("eilo.vad.runtime")
        val wrapper=System.getProperty("eilo.vad.wrapper")
        val runtimeSha=System.getProperty("eilo.vad.runtimeSha")
        val wrapperSha=System.getProperty("eilo.vad.wrapperSha")
        val base=NativeVadJni.loadVerified(listOf(runtime,wrapper)) {
            sha(model)=="6b99cbfd39246b6706f98ec13c7c50c6b299181f2474fa05cbc8046acc274396" && sha(runtime)==runtimeSha && sha(wrapper)==wrapperSha
        }
        var valid=true;var revokeAfter=false;var revokeOnClose=false
        var opens=0;var closes=0;var calls=0
        val api=object:NativeVadApi {
            override fun create(model:String):Long { val h=base.create(model);if(h>0)opens++;return h }
            override fun process(handle:Long,pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation? {
                calls++;val frame=base.process(handle,pcm,count,final);if(revokeAfter)valid=false;return frame
            }
            override fun destroy(handle:Long){closes++;base.destroy(handle);if(revokeOnClose)valid=false}
        }
        fun delivery()=VadWindowDelivery({valid},{NativeVadStream(model,{valid},api)})
        fun feed(d:VadWindowDelivery,count:Int,start:Int)=d.accept(FloatArray(count),count,start)
        val quiet=delivery()
        repeat(250){val event=feed(quiet,320,it*320);assertEquals(if(it==249)EndpointResult.NO_SPEECH else EndpointResult.CONTINUE,event.result);assertEquals(320,event.consumedSamples)}
        assertEquals(80000,quiet.acceptedSamples());assertEquals(0,quiet.retainedSamples());assertEquals(1,opens);assertEquals(1,closes)
        val odd=delivery();val sizes=listOf(1,511,320,1600,73);var position=0;var index=0;var last=EndpointResult.CONTINUE
        while(last==EndpointResult.CONTINUE){val count=sizes[index%sizes.size];val event=feed(odd,count,position);assertTrue(event.consumedSamples in 1..count);position+=event.consumedSamples;last=event.result;index++}
        assertEquals(80000,position);assertEquals(EndpointResult.NO_SPEECH,last);assertEquals(0,odd.retainedSamples())
        val eof=delivery();assertEquals(EndpointResult.CONTINUE,feed(eof,7,0).result)
        assertEquals(EndpointResult.INCOMPLETE,eof.finish().result);assertEquals(7,eof.acceptedSamples());assertEquals(0,eof.retainedSamples())
        val revoked=delivery();revokeAfter=true;val rejected=feed(revoked,512,0)
        assertEquals(EndpointResult.INVALID,rejected.result);assertEquals(0,rejected.consumedSamples);assertEquals(0,revoked.retainedSamples())
        valid=true;revokeAfter=false;val before=calls
        assertEquals(EndpointResult.INVALID,feed(revoked,512,0).result);assertEquals(before,calls)
        val cleanup=delivery();assertEquals(EndpointResult.CONTINUE,feed(cleanup,7,0).result);revokeOnClose=true
        assertEquals(EndpointResult.INVALID,cleanup.finish().result);assertEquals(0,cleanup.retainedSamples());valid=true
        assertEquals(EndpointResult.INVALID,cleanup.finish().result)
        assertEquals(5,opens);assertEquals(5,closes);assertEquals(317,calls)
        val first=base.create(model);assertTrue(first>0);assertNotNull(base.process(first,FloatArray(512),512,true));base.destroy(first)
        assertNull(base.process(first,FloatArray(512),512,false));base.destroy(first)
        val second=base.create(model);assertTrue(second>first);assertNull(base.process(first,FloatArray(512),512,false))
        assertEquals(0,base.process(second,FloatArray(512),512,false)?.startSample)
        assertNull(base.process(second,FloatArray(513),513,false));assertNull(base.process(second,FloatArray(512),512,false));base.destroy(second)
        File(System.getProperty("eilo.vad.result")).writeText("""{"scope":"MACOS_JVM_NATIVE_JNI_WORKER","synthetic":true,"quiet_valid_samples":80000,"odd_chunk_valid_samples":80000,"eof_valid_samples":7,"native_calls":317,"opens":5,"closes":5,"revocation_rejected":true,"cleanup_revocation_rejected":true,"jni_stale_handle_rejected":true,"jni_invalid_count_revoked":true,"physical":"NOT_RUN"}"""+"\n")
    }
}
