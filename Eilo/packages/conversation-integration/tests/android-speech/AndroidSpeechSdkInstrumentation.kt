package com.eilo.foundation
import android.app.Instrumentation
import android.os.Bundle
import android.os.SystemClock
import android.content.pm.PackageManager
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import java.util.concurrent.atomic.AtomicInteger
import org.json.JSONObject

/** Existing SDK/voice readiness only. Never opens microphone or requests a download. */
class AndroidSpeechSdkInstrumentation:Instrumentation(){
    override fun onCreate(arguments:Bundle?){super.onCreate(arguments);start()}
    override fun onStart(){
        val result=Bundle();var stage="setup";var speech:AndroidOfflineSpeech?=null;var backend:AndroidSystemSpeech?=null;var passed=false
        val report=File(targetContext.filesDir,"speech-sdk-results.json")
        try{
            check(targetContext.checkSelfPermission(android.Manifest.permission.INTERNET)==PackageManager.PERMISSION_DENIED)
            check(targetContext.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_DENIED)
            check(!report.exists());stage="sdk-initialize"
            runOnMainSync{backend=AndroidSystemSpeech(targetContext)}
            val system=backend!!;val voices=AtomicReference<List<OfflineVoice>>(emptyList())
            val deadline=SystemClock.elapsedRealtime()+15000
            while(SystemClock.elapsedRealtime()<deadline){val found=system.voices();if(found.isNotEmpty()){voices.set(found);break};Thread.sleep(100)}
            val registry=OfflineVoiceRegistry();val ready=registry.refresh(voices.get())
            val data=JSONObject().put("scope","ANDROID_EMULATOR_SPEECH_SDK").put("physical","NOT_RUN")
                .put("network_acceptance","NOT_RUN").put("acoustic_acceptance","NOT_RUN").put("production","NOT_ENABLED")
                .put("microphone","NOT_USED").put("eligible_voice",ready).put("download_requested",false)
                .put("sdk_completed",false).put("sdk_started",0).put("sdk_finished",0).put("status",if(ready)"PENDING" else "BLOCKED_OFFLINE_VOICE_MISSING")
            if(ready){
                stage="sdk-prepare";val token=GenerationToken(java.util.UUID.randomUUID(),java.util.UUID.randomUUID(),1,1)
                val adapter=AndroidOfflineSpeech(system,allowed={!it.cancelled});speech=adapter
                val prepared=CountDownLatch(1);var accepted=false
                adapter.refresh(registry.selection()!!.voice.id){accepted=it;prepared.countDown()}
                check(prepared.await(10,TimeUnit.SECONDS)&&accepted)
                stage="sdk-fixed-clause";val done=CountDownLatch(1);val started=AtomicInteger();val finished=AtomicInteger();val failed=AtomicInteger()
                check(adapter.enqueue(token,"This is a local evaluation.",gain=0f){event->when(event){
                    OfflineSpeechEvent.STARTED->started.incrementAndGet()
                    OfflineSpeechEvent.FINISHED->{finished.incrementAndGet();done.countDown()}
                    else->{failed.incrementAndGet();done.countDown()}}})
                check(done.await(45,TimeUnit.SECONDS)&&started.get()==1&&finished.get()==1&&failed.get()==0)
                adapter.close();speech=null
                data.put("status","SDK_CALLBACKS_COMPLETED").put("sdk_completed",true).put("sdk_started",started.get()).put("sdk_finished",finished.get())
                // gain=0 + emulator -no-audio: this proves SDK events, never audible output.
            }
            report.writeText(data.toString()+"\n");passed=true
        }catch(error:Throwable){report.delete();result.putString("stage",stage);result.putString("failure_type",error.javaClass.simpleName)}
        finally{try{speech?.close();if(speech==null)backend?.shutdown()}catch(_:Throwable){passed=false;report.delete()}}
        result.putString("eilo_speech_sdk",if(passed)"PASS" else "FAIL");finish(if(passed)-1 else 0,result)
    }
}
