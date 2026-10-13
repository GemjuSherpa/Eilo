package com.eilo.foundation

import android.app.Instrumentation
import android.os.Bundle
import java.io.File
import java.util.UUID
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import org.json.JSONObject

/** Explicit temporary Debug evaluator; fixed generic speech only, no microphone. */
class OfflineSpeechEvaluationInstrumentation : Instrumentation() {
    override fun onCreate(arguments: Bundle?) { super.onCreate(arguments); start() }
    override fun onStart() {
        val output=Bundle();val report=File(targetContext.filesDir,"offline-speech-evaluation.json")
        var adapter:AndroidOfflineSpeech?=null
        try {
            report.delete()
            val factory=java.util.concurrent.Executors.newSingleThreadExecutor { Thread(it,"eilo-voice-probe").apply{isDaemon=true} }
            val driver=try { factory.submit<AndroidSystemSpeech> { AndroidSystemSpeech(targetContext) }.get(5,TimeUnit.SECONDS) }
                finally { factory.shutdown() }
            val speech=AndroidOfflineSpeech(driver,allowed={!it.cancelled});adapter=speech
            var ready=false
            val deadline=System.nanoTime()+TimeUnit.SECONDS.toNanos(20)
            do { val prepared=CountDownLatch(1)
                speech.refresh { ready=it;prepared.countDown() };check(prepared.await(6,TimeUnit.SECONDS))
                if(!ready)Thread.sleep(100)
            }while(!ready && System.nanoTime()<deadline)
            val result=JSONObject().put("task","VC-VOICE-02").put("platform","Android API35 ARM64 emulator")
                .put("offline_ready",ready)
                .put("microphone","NOT USED").put("physical_airplane_mode_and_traffic","NOT RUN")
                .put("engine_network_isolation","NOT VERIFIED; engine has separate OS permissions")
            if(ready){
                val selected=speech.registry.selection()!!;check(selected.voice.installed && selected.voice.networkRequired==false)
                val done=CountDownLatch(1);val status=AtomicReference<OfflineSpeechEvent?>()
                val token=GenerationToken(UUID.randomUUID(),UUID.randomUUID(),1,0)
                check(speech.enqueue(token,"This is a generic offline speech test."){event->
                    if(event!=OfflineSpeechEvent.STARTED){status.set(event);done.countDown()}
                })
                check(done.await(30,TimeUnit.SECONDS) && status.get()==OfflineSpeechEvent.FINISHED)
                token.cancelled=true;speech.cancel()
                result.put("exact_voice_network_flag",false).put("SDK_synthesis_completion","PASS")
            }else{
                check(!speech.enqueue(GenerationToken(UUID.randomUUID(),UUID.randomUUID(),1,0),"This is a generic offline speech test."){})
                result.put("SDK_synthesis_completion","NOT RUN; registry unavailable or no installed eligible voice").put("missing_voice_gate","PASS")
            }
            speech.close();report.writeText(result.toString(2));output.putString("eilo_offline_speech","PASS")
            finish(-1,output)
        }catch(_:Exception){report.delete();output.putString("eilo_offline_speech","FAIL");finish(0,output)}
        finally{adapter?.close()}
    }
}
