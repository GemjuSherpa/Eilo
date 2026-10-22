package com.eilo.foundation

import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import org.json.JSONArray
import org.json.JSONObject
import android.app.Instrumentation
import android.os.Bundle
import android.content.pm.PackageManager

/** Ephemeral ES256 lab pack with real verified weights, never production trust. */
private class CaptureRuntimePack(manifest:File):AutoCloseable {
    val root=File(manifest.parentFile,"signed-pack").apply{check(mkdir())}
    val key=java.security.KeyPairGenerator.getInstance("EC").apply{initialize(java.security.spec.ECGenParameterSpec("secp256r1"))}.generateKeyPair()
    val runtime="8345f333951c661d166b00e6f9362e553768f292";val evidence="c".repeat(64)
    val rows=JSONArray(manifest.readText())
    val pins=(0 until rows.length()).filter{rows.getJSONObject(it).getString("id")!="llm"}.map{val r=rows.getJSONObject(it);SpeechArtifactPin(r.getString("id"),r.getString("filename"),r.getString("sha256"),r.getLong("bytes"),evidence)}
    val sources=(0 until rows.length()).map{File(manifest.parentFile,"inputs/"+rows.getJSONObject(it).getString("filename"))}
    val store=PackStore(File(root,"store"),mapOf("lab-key" to key.public.encoded),runtime,setOf(evidence))
    val vad=SpeechPackSelection("lab-speech",runtime,SpeechPackKind.VAD,pins.filter{it.id=="vad"})
    val llmRow=(0 until rows.length()).map{rows.getJSONObject(it)}.single{it.getString("id")=="llm"}
    val llm=LlmPackSelection("lab-speech",runtime,LlmArtifactPin("llm",llmRow.getString("sha256"),llmRow.getLong("bytes"),evidence))
    val asr=SpeechPackSelection("lab-speech",runtime,SpeechPackKind.ASR,pins.filter{it.id!="vad"})
    init{activate(1)}
    fun activate(revision:Int){
        val artifacts=JSONArray()
        for(i in 0 until rows.length()){val p=rows.getJSONObject(i);val id=p.getString("id");val filename=p.getString("filename")
            artifacts.put(JSONObject().put("id",id).put("filename",filename)
            .put("role",if(id=="llm")"llm" else if(id=="vad")"vad" else if(filename=="tokenizer.bin")"tokenizer" else "asr")
            .put("url","https://models.example.test/"+filename).put("sha256",p.getString("sha256")).put("bytes",p.getLong("bytes"))
            .put("license",if(id=="llm")"Apache-2.0" else "MIT").put("licenseEvidence",evidence))}
        val data=JSONObject().put("schema",1).put("packId","lab-speech").put("revision",revision)
            .put("runtimeRevision",runtime).put("minAndroid",35).put("minIos",18).put("artifacts",artifacts).toString().replace("\\/","/").toByteArray()
        val signer=java.security.Signature.getInstance("SHA256withECDSA");signer.initSign(key.private);signer.update(data)
        val pack=VerifiedPack.verify(data,signer.sign(),"lab-key","ES256",mapOf("lab-key" to key.public.encoded),runtime)
        store.activate(pack,sources.indices.map{VerifiedArtifact.verify(pack,it,sources[it])},PackCancellation())
    }
    override fun close(){check(root.deleteRecursively())}
}

/** File-fed real VAD/ASR/LLM with a synthetic asynchronous clause sink, never TTS. */
class CaptureReplyInstrumentation:Instrumentation(){
    private var stage="setup"
    override fun onCreate(arguments:Bundle?){super.onCreate(arguments);start()}
    private fun digest(bytes:ByteArray)=MessageDigest.getInstance("SHA-256").digest(bytes).joinToString(""){"%02x".format(it)}
    private class Effects:ControllerEffects{
        override fun startCapture()=true
        override fun playClause(clause:String){error("unexpected speech")}
        override fun cancelWork(){}
        override fun releaseCapture(){}
        override fun clearVolatileContext(){}
    }
    override fun onStart(){
        val work=File(targetContext.filesDir,"capture-reply-art");val report=File(targetContext.filesDir,"capture-reply-art-results.json")
        val result=Bundle();var passed=false
        val worker=Executors.newSingleThreadExecutor{Thread(it,"joined-inference")}
        val playback=Executors.newSingleThreadExecutor{Thread(it,"synthetic-playback")}
        var controller:NativeController?=null
        try{
            check(targetContext.checkSelfPermission(android.Manifest.permission.INTERNET)==PackageManager.PERMISSION_DENIED)
            check(targetContext.checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_DENIED)
            check(!report.exists());val config=JSONObject(File(work,"input.json").readText())
            val directory=File(targetContext.applicationInfo.nativeLibraryDir)
            val names=listOf("libonnxruntime.so","libeilo_vad_jni.so","libmoonshine.so","libeilo_asr_jni.so","libeilo_llm_jni.so")
            val keys=listOf("runtime","vadJni","asrCore","asrJni","llmJni")
            val verified={names.indices.all{digest(File(directory,names[it]).readBytes())==config.getString(keys[it]+"Sha")}}
            check(verified());stage="native-load"
            val vb=NativeVadJni.loadVerified(listOf(names[0],names[1]).map{File(directory,it).absolutePath},verified)
            val ab=NativeAsrJni.loadVerified(listOf(names[0],names[2],names[3]).map{File(directory,it).absolutePath},verified)
            val base=NativeLlmRuntime(evaluationEnabled=true).load() ?: error("native unavailable")
            fun onWorker(){check(Thread.currentThread().name=="joined-inference")}
            val llm=object:NativeLlmApi by base{
                override fun load(handle:Long,descriptor:Int,threads:Int):Int{onWorker();return base.load(handle,descriptor,threads)}
                override fun begin(handle:Long,prompt:ByteArray,count:Int,outputLimit:Int):Int{onWorker();return base.begin(handle,prompt,count,outputLimit)}
                override fun next(handle:Long,output:ByteArray,count:IntArray):Int{onWorker();return base.next(handle,output,count)}
                override fun destroy(handle:Long){onWorker();base.destroy(handle)}
            }
            val va=object:NativeVadApi by vb{
                override fun create(model:String):Long{onWorker();return vb.create(model)}
                override fun process(handle:Long,pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation?{onWorker();return vb.process(handle,pcm,count,final)}
                override fun destroy(handle:Long){onWorker();vb.destroy(handle)}
            }
            val aa=object:NativeAsrApi by ab{
                override fun create(directory:String):Long{onWorker();return ab.create(directory)}
                override fun accept(handle:Long,pcm:FloatArray,count:Int):Int{onWorker();return ab.accept(handle,pcm,count)}
                override fun text(handle:Long,finish:Boolean):ByteArray?{onWorker();return ab.text(handle,finish)}
                override fun destroy(handle:Long){onWorker();ab.destroy(handle)}
            }
            stage="signed-pack"
            CaptureRuntimePack(File(work,"manifest.json")).use{pack->
                val clock=java.util.concurrent.atomic.AtomicLong();val effects=Effects();val c=NativeController(effects=effects,clock=NativeClock{clock.get()},scheduler=IdleScheduler{_,_->IdleCancellation{}},
                    permission=object:MicrophonePermissionAdapter{override fun status()=MicrophonePermission.GRANTED
                        override fun request(completion:(MicrophonePermission)->Unit){error("no permission request")}},models=ModelReadinessAdapter{ModelStatus.READY})
                controller=c
                check(c.dispatch(ControllerEvent.START));check(c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token()))
                val raw=File(work,"synthetic.f32").readBytes();check(raw.size==37228*4)
                val input=ShortArray(raw.size/4);val buffer=ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN)
                input.indices.forEach{val f=buffer.float;check(f.isFinite()&&f in -1f..1f);input[it]=(f*32768).toInt().toShort()};raw.fill(0)
                val cases=JSONArray()
                try{for(phase in listOf("speech16","followup48","quiet")){
                    stage=phase;val token=c.token()!!;val rate=if(phase=="followup48")48000 else 16000
                    val slot=VadCaptureSlot(rate);var final:AsrText?=null;var metadata=0;var outcome:VadCaptureOutcome?=null
                    fun barrier(){worker.submit{}.get(60,TimeUnit.SECONDS)}
                    try{
                        val ticket=slot.prepare(effects,c,token)!!
                        check(worker.submit<Boolean>{SpeechCaptureInstaller.install(ticket,pack.store,pack.vad,pack.store,pack.asr,worker,va,aa,
                            accepted={metadata++;outcome=it},recognized={final=it})}.get(60,TimeUnit.SECONDS))
                        var pcm=if(phase=="quiet")ShortArray(80000) else input+ShortArray(32000)
                        if(rate==48000){val original=pcm;pcm=ShortArray(original.size*3){original[it/3]};original.fill(0)}
                        try{var offset=0;while(offset<pcm.size){val end=minOf(offset+if(rate==48000)960 else 320,pcm.size)
                            val chunk=pcm.copyOfRange(offset,end);try{slot.submit(chunk,chunk.size,rate)}finally{chunk.fill(0)};barrier();offset=end}
                            slot.finish();barrier()
                        }finally{pcm.fill(0)}
                        check(metadata==1);var starts=0;val clauses=java.util.concurrent.atomic.AtomicInteger();var submitted=false;var completed=false;var hash=""
                        val text=final
                        if(text!=null){
                            hash=digest(text.text.toByteArray())
                            val sink=object:NativeClauseSink{
                                override fun enqueue(token:GenerationToken,text:String,event:(OfflineSpeechEvent)->Unit):Boolean{
                                    check(text.isNotBlank());clauses.incrementAndGet();playback.execute{event(OfflineSpeechEvent.STARTED);event(OfflineSpeechEvent.FINISHED)};return true}
                                override fun cancel(){}
                            }
                            val local=GenericSpokenTurn.localReply(c,worker,pack.store,pack.llm,llm,limit=96)
                            val turn=GenericSpokenTurn(c,token,sink,true,GenericReplyStarter{t,r,consume,finish->starts++;local.start(t,r,consume,finish)})
                            submitted=turn.submit(text,0.95f);check(submitted && !turn.submit(text,0.95f))
                            val deadline=android.os.SystemClock.elapsedRealtime()+240000
                            while(c.state() !in listOf(ControllerState.STANDBY,ControllerState.ERROR,ControllerState.STOPPED) && android.os.SystemClock.elapsedRealtime()<deadline)Thread.sleep(20)
                            check(c.state()==ControllerState.STANDBY && starts==1 && clauses.get()>0);completed=true
                            clock.addAndGet(1000);check(c.beginGenericFollowup(c.token()!!)!=null)
                        }else check(phase=="quiet" && outcome?.result==EndpointResult.NO_SPEECH && c.state()==ControllerState.CAPTURING)
                        cases.put(JSONObject().put("case",phase).put("recognized",if(text==null)0 else 1).put("metadata",metadata)
                            .put("normalized_samples",outcome?.totalSamples ?: 0).put("llm_starts",starts).put("reply_submitted",submitted)
                            .put("completed",completed).put("clauses",clauses.get()).put("transcript_sha256",hash)
                            .put("context_messages",c.genericContext(c.token()!!)?.size ?: 0).put("worker_verified",true))
                    }finally{slot.close();barrier()}
                }}finally{input.fill(0)}
                check(c.endConversation());c.stop()
                report.writeText(JSONObject().put("scope","ANDROID_ART_SIGNED_CAPTURE_REPLY").put("physical","NOT_RUN").put("production","NOT_ENABLED")
                    .put("microphone","NOT_USED").put("confidence","SYNTHETIC_0_95").put("speech_sink","SYNTHETIC_NO_SDK").put("cases",cases).toString()+"\n")
            };passed=true
        }catch(error:Throwable){result.putString("stage",stage);result.putString("failure_type",error.javaClass.simpleName);report.delete()}
        finally{
            controller?.stop();worker.shutdown();playback.shutdown()
            if(!worker.awaitTermination(60,TimeUnit.SECONDS) || !playback.awaitTermination(30,TimeUnit.SECONDS) || !work.deleteRecursively()){passed=false;report.delete()}
        }
        result.putString("eilo_capture_reply_art",if(passed)"PASS" else "FAIL");finish(if(passed)-1 else 0,result)
    }
}
