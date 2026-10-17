package com.eilo.foundation

import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.MessageDigest
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Ephemeral ES256 lab pack with real verified weights, never production trust. */
private class InstallerRuntimePack(manifest:File):AutoCloseable {
    val root=java.nio.file.Files.createTempDirectory("eilo-speech-installer").toFile()
    val key=java.security.KeyPairGenerator.getInstance("EC").apply{initialize(java.security.spec.ECGenParameterSpec("secp256r1"))}.generateKeyPair()
    val runtime="a".repeat(40);val evidence="c".repeat(64)
    val rows=JSONArray(manifest.readText())
    val pins=(0 until rows.length()).map{val r=rows.getJSONObject(it);SpeechArtifactPin(r.getString("id"),r.getString("filename"),r.getString("sha256"),r.getLong("bytes"),evidence)}
    val sources=(0 until rows.length()).map{File(rows.getJSONObject(it).getString("source"))}
    val store=PackStore(File(root,"store"),mapOf("lab-key" to key.public.encoded),runtime,setOf(evidence))
    val vad=SpeechPackSelection("lab-speech",runtime,SpeechPackKind.VAD,pins.filter{it.id=="vad"})
    val asr=SpeechPackSelection("lab-speech",runtime,SpeechPackKind.ASR,pins.filter{it.id!="vad"})
    init{activate(1)}
    fun activate(revision:Int){
        val artifacts=JSONArray()
        pins.forEach{p->artifacts.put(JSONObject().put("id",p.id).put("filename",p.filename)
            .put("role",if(p.id=="vad")"vad" else if(p.filename=="tokenizer.bin")"tokenizer" else "asr")
            .put("url","https://models.example.test/"+p.filename).put("sha256",p.sha256).put("bytes",p.bytes)
            .put("license","MIT").put("licenseEvidence",evidence))}
        val data=JSONObject().put("schema",1).put("packId","lab-speech").put("revision",revision)
            .put("runtimeRevision",runtime).put("minAndroid",35).put("minIos",18).put("artifacts",artifacts).toString().toByteArray()
        val signer=java.security.Signature.getInstance("SHA256withECDSA");signer.initSign(key.private);signer.update(data)
        val pack=VerifiedPack.verify(data,signer.sign(),"lab-key","ES256",mapOf("lab-key" to key.public.encoded),runtime)
        store.activate(pack,pins.indices.map{VerifiedArtifact.verify(pack,it,sources[it])},PackCancellation())
    }
    override fun close(){check(root.deleteRecursively())}
}

/** File-fed macOS host JNI, not Android ART, OS capture or acoustic acceptance. */
class NativeSpeechInstallerRuntimeTest {
    private fun property(name:String)=System.getProperty("eilo.installer."+name) ?: error("opt-in property required")
    private fun digest(bytes:ByteArray)=MessageDigest.getInstance("SHA-256").digest(bytes).joinToString(""){"%02x".format(it)}
    @Test fun eightRealSignedInstallerCases(){
        val libraries=listOf("runtime","vadJni","asrCore","asrJni")
        val verified={libraries.all{digest(File(property(it)).readBytes())==property(it+"Sha")}}
        val vbase=NativeVadJni.loadVerified(listOf(property("runtime"),property("vadJni")),verified)
        val abase=NativeAsrJni.loadVerified(listOf(property("runtime"),property("asrCore"),property("asrJni")),verified)
        val raw=File(property("audio")).readBytes();assertTrue(raw.isNotEmpty() && raw.size%4==0 && raw.size<=480000*4)
        val input=ShortArray(raw.size/4);val buffer=ByteBuffer.wrap(raw).order(ByteOrder.LITTLE_ENDIAN)
        input.indices.forEach{val value=buffer.float;assertTrue(value.isFinite() && value in -1f..1f);input[it]=(value*32768).toInt().toShort()};raw.fill(0)
        val worker=Executors.newSingleThreadExecutor{r->Thread(r,"signed-speech-inference")}
        fun onWorker(){assertEquals("signed-speech-inference",Thread.currentThread().name)}
        fun barrier(){worker.submit{}.get(30,TimeUnit.SECONDS)}
        val results=JSONArray()
        try{InstallerRuntimePack(File(property("manifest"))).use{pack->
            for(phase in listOf("speech16","speech48","quiet","stop-final","replace-final","idle-stop","stale-ticket","corrupt-pack")){
                val effects=EffectsSpy();val c=testController(effects=effects)
                assertTrue(c.dispatch(ControllerEvent.START));assertTrue(c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token()))
                val token=c.token()!!;val rate=if(phase=="speech48")48000 else 16000;val slot=VadCaptureSlot(rate)
                var vo=0;var vc=0;var ao=0;var ac=0;var vadCalls=0;var asrCalls=0;var finals=0;var texts=0;var metadata=0
                var textDigest="";var outcome:VadCaptureOutcome?=null
                val va=object:NativeVadApi{
                    override fun create(model:String):Long{onWorker();val h=vbase.create(model);if(h>0)vo++;return h}
                    override fun process(handle:Long,pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation?{onWorker();vadCalls++;return vbase.process(handle,pcm,count,final)}
                    override fun destroy(handle:Long){onWorker();vc++;vbase.destroy(handle)}
                }
                val aa=object:NativeAsrApi{
                    override fun create(directory:String):Long{onWorker();val h=abase.create(directory);if(h>0)ao++;return h}
                    override fun accept(handle:Long,pcm:FloatArray,count:Int):Int{onWorker();asrCalls++;return abase.accept(handle,pcm,count)}
                    override fun text(handle:Long,finish:Boolean):ByteArray?{
                        onWorker();val result=abase.text(handle,finish)
                        if(finish){finals++;if(phase=="stop-final")c.stop();if(phase=="replace-final")pack.activate(2)}
                        return result
                    }
                    override fun destroy(handle:Long){onWorker();ac++;abase.destroy(handle)}
                }
                try{
                    val ticket=slot.prepare(effects,c,token)!!
                    if(phase=="stale-ticket")slot.detach()
                    if(phase=="corrupt-pack")pack.store.verifiedFiles()!!.second.last().writeBytes(byteArrayOf(0))
                    val installed=worker.submit<Boolean>{SpeechCaptureInstaller.install(ticket,pack.store,pack.vad,pack.store,pack.asr,worker,va,aa,
                        accepted={metadata++;outcome=it},recognized={assertTrue(it.text.isNotEmpty());texts++;textDigest=digest(it.text.toByteArray())})}.get(60,TimeUnit.SECONDS)
                    val denied=phase=="stale-ticket" || phase=="corrupt-pack"
                    assertEquals(!denied,installed)
                    if(!denied){
                        var pcm=if(phase=="quiet" || phase=="idle-stop")ShortArray(if(phase=="quiet")80000 else 512) else input+ShortArray(32000)
                        if(rate==48000){val original=pcm;pcm=ShortArray(original.size*3){original[it/3]};original.fill(0)}
                        try{var offset=0;while(offset<pcm.size){val end=minOf(offset+if(rate==48000)960 else 320,pcm.size)
                            val chunk=pcm.copyOfRange(offset,end);try{slot.submit(chunk,chunk.size,rate)}finally{chunk.fill(0)}
                            barrier();offset=end}
                            if(phase=="idle-stop")c.stop() else slot.finish();barrier()
                        }finally{pcm.fill(0)}
                        when(phase){
                            "speech16","speech48"->{assertEquals(1,texts);assertEquals(1,metadata);assertEquals(EndpointResult.COMPLETE,outcome?.result)}
                            "quiet"->{assertEquals(0,ao);assertEquals(1,metadata);assertEquals(EndpointResult.NO_SPEECH,outcome?.result)}
                            "idle-stop"->{assertEquals(0,ao);assertEquals(0,metadata)}
                            else->{assertEquals(1,ao);assertEquals(1,finals);assertEquals(0,texts);assertEquals(0,metadata)}
                        }
                    }
                    slot.close();barrier();assertEquals(vo,vc);assertEquals(ao,ac)
                    results.put(JSONObject().put("case",phase).put("installed",installed).put("vad_opens",vo).put("vad_closes",vc)
                        .put("vad_calls",vadCalls).put("asr_opens",ao).put("asr_closes",ac).put("asr_accept_calls",asrCalls)
                        .put("asr_finals",finals).put("recognized",texts).put("metadata",metadata).put("transcript_sha256",textDigest)
                        .put("source_rate",rate).put("normalized_samples",outcome?.totalSamples ?: 0))
                }finally{slot.close();barrier()}
            }
        }}finally{input.fill(0);worker.shutdown();assertTrue(worker.awaitTermination(30,TimeUnit.SECONDS))}
        File(property("result")).writeText(JSONObject().put("scope","MACOS_JVM_JNI_SIGNED_SPEECH_INSTALLER")
            .put("synthetic",true).put("worker_verified",true).put("physical","NOT_RUN").put("production","NOT_ENABLED")
            .put("lab_signing","EPHEMERAL_ES256").put("cases",results).toString()+"\n")
    }
}
