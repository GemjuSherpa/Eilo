package com.eilo.foundation

import java.io.File
import java.nio.file.Files
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class SpeechPackLeaseTest {
    private class Fixture:AutoCloseable {
        val root=Files.createTempDirectory("speech-pack-test").toFile()
        val key=KeyPairGenerator.getInstance("EC").apply{initialize(ECGenParameterSpec("secp256r1"))}.generateKeyPair()
        val runtime="a".repeat(40);val evidence="c".repeat(64)
        val names=listOf("adapter.ort","cross_kv.ort","decoder_kv.ort","encoder.ort","frontend.model.ort","frontend.weights.ort","streaming_config.json","tokenizer.bin").sorted()+"silero.onnx"
        val sources=names.mapIndexed{i,name->File(root,name).apply{writeBytes(byteArrayOf(i.toByte(),2,3,4))}}
        val pins=names.mapIndexed{i,name->SpeechArtifactPin("asset-$i",name,sha(sources[i]),4,evidence)}
        val store=PackStore(File(root,"store"),mapOf("test-key" to key.public.encoded),runtime,setOf(evidence))
        fun selection(kind:SpeechPackKind,pins:List<SpeechArtifactPin> = if(kind==SpeechPackKind.VAD)listOf(this.pins.last())else this.pins.dropLast(1),pack:String="test-pack",rr:String=runtime)=SpeechPackSelection(pack,rr,kind,pins)
        fun activate(revision:Int=1,wrongRole:Boolean=false,wrongLicense:Boolean=false,wrongAsrRole:Boolean=false) {
            val artifacts=JSONArray()
            for(pin in pins.reversed()) {
                val role=if(pin.filename=="silero.onnx"){if(wrongRole)"asr" else "vad"}else if(pin.filename=="tokenizer.bin")"tokenizer" else if(wrongAsrRole && pin.filename=="streaming_config.json")"wake" else "asr"
                artifacts.put(JSONObject().put("id",pin.id).put("filename",pin.filename).put("role",role).put("url","https://models.example.test/"+pin.filename).put("sha256",pin.sha256).put("bytes",pin.bytes).put("license",if(wrongLicense)"Apache-2.0" else "MIT").put("licenseEvidence",evidence))
            }
            val data=JSONObject().put("schema",1).put("packId","test-pack").put("revision",revision).put("runtimeRevision",runtime).put("minAndroid",35).put("minIos",18).put("artifacts",artifacts).toString().toByteArray()
            val signer=Signature.getInstance("SHA256withECDSA");signer.initSign(key.private);signer.update(data)
            val pack=VerifiedPack.verify(data,signer.sign(),"test-key","ES256",mapOf("test-key" to key.public.encoded),runtime)
            store.activate(pack,pack.manifest.artifacts.mapIndexed{i,a->VerifiedArtifact.verify(pack,i,sources[names.indexOf(a.filename)])},PackCancellation())
        }
        fun lease(kind:SpeechPackKind)=SpeechPackLease.resolve(store,selection(kind))
        override fun close(){root.deleteRecursively()}
        companion object{fun sha(file:File)=MessageDigest.getInstance("SHA-256").digest(file.readBytes()).joinToString(""){"%02x".format(it)}}
    }
    private fun rejects(action:()->Unit){assertThrows(IllegalStateException::class.java,action)}
    @Test fun shuffledSignedVadAndCompleteAsrResolve() {Fixture().use{f->
        f.activate();val vad=f.lease(SpeechPackKind.VAD);val asr=f.lease(SpeechPackKind.ASR);var vc=0;var ac=0
        val api=object:NativeVadApi {
            override fun create(model:String):Long{assertTrue(model.endsWith("/silero.onnx"));return 1}
            override fun process(handle:Long,pcm:FloatArray,count:Int,final:Boolean)=NativeVadObservation(0.1f,0,count,final)
            override fun destroy(handle:Long){vc++}
        }
        vad.openVad({true},api).process(FloatArray(512),512,true)
        val aa=object:NativeAsrApi {
            override fun create(directory:String):Long{SpeechPackSelection.asrNames.forEach{assertTrue(File(directory,it).isFile)};return 2}
            override fun accept(handle:Long,pcm:FloatArray,count:Int)=0
            override fun text(handle:Long,finish:Boolean)=byteArrayOf(65)
            override fun destroy(handle:Long){ac++}
        }
        val a=asr.openAsr({true},aa);assertEquals("A",a.text(true));a.close();assertEquals(1,vc);assertEquals(1,ac)
        rejects{vad.openAsr({true})};rejects{asr.openVad({true})};vad.close();asr.close();assertFalse(vad.verified());assertFalse(asr.verified())
    }}
    @Test fun exactPinsPackRuntimeBytesHashAndEvidenceRequired(){Fixture().use{f->
        f.activate();val p=f.pins.last()
        for(bad in listOf(p.copy(id="missing"),p.copy(sha256="d".repeat(64)),p.copy(bytes=5),p.copy(licenseEvidence="d".repeat(64))))rejects{SpeechPackLease.resolve(f.store,f.selection(SpeechPackKind.VAD,listOf(bad)))}
        rejects{SpeechPackLease.resolve(f.store,f.selection(SpeechPackKind.ASR,pack="other"))};rejects{SpeechPackLease.resolve(f.store,f.selection(SpeechPackKind.ASR,rr="b".repeat(40)))}
        assertThrows(IllegalArgumentException::class.java){f.selection(SpeechPackKind.ASR,f.pins.dropLast(2))};assertThrows(IllegalArgumentException::class.java){f.selection(SpeechPackKind.VAD,listOf(p,p))}
        assertThrows(UnsupportedOperationException::class.java){(SpeechPackSelection.asrNames as MutableSet).clear()}
    }}
    @Test fun untrustedUnlicensedMissingAndCorruptStoresDenied(){Fixture().use{f->
        rejects{f.lease(SpeechPackKind.ASR)};f.activate()
        for(store in listOf(PackStore(File(f.root,"store"),emptyMap(),f.runtime,setOf(f.evidence)),PackStore(File(f.root,"store"),mapOf("test-key" to f.key.public.encoded),f.runtime)))rejects{SpeechPackLease.resolve(store,f.selection(SpeechPackKind.ASR))}
        f.store.verifiedFiles()!!.second[0].writeBytes(byteArrayOf(9));rejects{f.lease(SpeechPackKind.ASR)}
    }}
    @Test fun signedWrongRoleOrLicenseIsDenied(){for(wrongRole in listOf(false,true))Fixture().use{f->f.activate(wrongRole=wrongRole,wrongLicense=!wrongRole);rejects{f.lease(SpeechPackKind.VAD)};if(!wrongRole)rejects{f.lease(SpeechPackKind.ASR)}};Fixture().use{f->f.activate(wrongAsrRole=true);rejects{f.lease(SpeechPackKind.ASR)}}}
    @Test fun identicalFilesNewEpochAndCloseCannotReviveLease(){Fixture().use{f->
        f.activate();val old=f.lease(SpeechPackKind.ASR);f.activate(2);assertFalse(old.verified());rejects{old.openAsr({true})}
        val fresh=f.lease(SpeechPackKind.ASR);assertTrue(fresh.verified());fresh.close();assertFalse(fresh.verified())
    }}
    @Test fun revocationDuringCreateAndProcessClosesNativeOwner(){for(duringCreate in listOf(false,true))Fixture().use{f->
        f.activate();val lease=f.lease(SpeechPackKind.VAD);var closes=0
        val api=object:NativeVadApi {
            override fun create(model:String):Long{if(duringCreate)lease.close();return 1}
            override fun process(handle:Long,pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation{lease.close();return NativeVadObservation(0.1f,0,count,final)}
            override fun destroy(handle:Long){closes++}
        }
        if(duringCreate)rejects{lease.openVad({true},api)}else{val v=lease.openVad({true},api);rejects{v.process(FloatArray(512),512,false)}}
        assertEquals(1,closes)
    }}
    @Test fun asrFinalRevocationAndDeniedCapabilityCannotReleaseText(){Fixture().use{f->
        f.activate();val lease=f.lease(SpeechPackKind.ASR);var creates=0;var closes=0
        val api=object:NativeAsrApi {
            override fun create(directory:String):Long{creates++;return 1}
            override fun accept(handle:Long,pcm:FloatArray,count:Int)=0
            override fun text(handle:Long,finish:Boolean):ByteArray{lease.close();return byteArrayOf(65)}
            override fun destroy(handle:Long){closes++}
        }
        rejects{lease.openAsr({false},api)};assertEquals(0,creates)
        val a=lease.openAsr({true},api);rejects{a.text(true)};assertEquals(1,closes);a.close();assertEquals(1,closes)
    }}
    private class CaptureHarness {
        val e=EffectsSpy();val tasks=ArrayDeque<Runnable>();val w=java.util.concurrent.Executor{tasks.add(it)}
        val slot=VadCaptureSlot(16000);val c=testController(effects=e)
        var samples=0;var vc=0;var ac=0;var vd=0;var ad=0;var texts=0;var outcomes=0
        var duringVad:()->Unit={};var duringAsrClose:()->Unit={}
        init{c.dispatch(ControllerEvent.START);c.dispatch(ControllerEvent.SPEECH_DETECTED,token=c.token())}
        val vad=object:NativeVadApi {
            override fun create(model:String):Long{vc++;return 1}
            override fun process(handle:Long,pcm:FloatArray,count:Int,final:Boolean):NativeVadObservation {
                val start=samples;samples+=count;duringVad()
                return NativeVadObservation(if(start<5120)0.95f else 0.01f,start,count,final)
            }
            override fun destroy(handle:Long){vd++}
        }
        val asr=object:NativeAsrApi {
            override fun create(directory:String):Long{ac++;return 2}
            override fun accept(handle:Long,pcm:FloatArray,count:Int)=0
            override fun text(handle:Long,finish:Boolean)=byteArrayOf(65)
            override fun destroy(handle:Long){ad++;duringAsrClose()}
        }
        fun install(f:Fixture,ticket:VadCaptureSlot.SetupTicket=slot.prepare(e,c,c.token()!!)!!,
            asrSelection:SpeechPackSelection=f.selection(SpeechPackKind.ASR))=SpeechCaptureInstaller.install(
                ticket,f.store,f.selection(SpeechPackKind.VAD),f.store,asrSelection,w,vad,asr,{outcomes++},{texts++})
        fun run(){while(tasks.isNotEmpty())tasks.removeFirst().run()}
        fun feed(){slot.submit(ShortArray(1600),1600,16000);run()}
    }
    @Test fun signedInstallerRunsJoinedTurnAndTicketCannotBeReused(){Fixture().use{f->
        f.activate();val h=CaptureHarness();val ticket=h.slot.prepare(h.e,h.c,h.c.token()!!)!!
        assertTrue(h.install(f,ticket));assertEquals(0,h.vc);repeat(20){h.feed()}
        assertEquals(1,h.texts);assertEquals(1,h.outcomes);assertEquals(1,h.vc);assertEquals(1,h.ac)
        assertEquals(1,h.vd);assertEquals(1,h.ad);assertFalse(h.install(f,ticket));h.run()
    }}
    @Test fun signedInstallerRejectsStaleWrongKindAndMissingSecondPack(){Fixture().use{f->
        f.activate();val h=CaptureHarness();val old=h.slot.prepare(h.e,h.c,h.c.token()!!)!!
        h.slot.detach();assertFalse(h.install(f,old));assertFalse(h.install(f,asrSelection=f.selection(SpeechPackKind.VAD)))
        assertFalse(h.install(f,asrSelection=f.selection(SpeechPackKind.ASR,pack="missing")))
        assertEquals(0,h.vc);assertEquals(0,h.ac);assertTrue(h.install(f));h.c.stop();h.run();assertEquals(0,h.vc)
    }}
    @Test fun signedInstallerRevocationAtVadAndAsrCleanupSuppressesText(){repeat(3){phase->Fixture().use{f->
        f.activate();val h=CaptureHarness();assertTrue(h.install(f))
        if(phase==0)f.activate(2)
        if(phase==1)h.duringVad={h.c.stop()}
        if(phase==2)h.duringAsrClose={h.c.stop()}
        repeat(20){h.feed()};assertEquals(0,h.texts);assertEquals(0,h.outcomes)
        assertEquals(h.vc,h.vd);assertEquals(h.ac,h.ad);h.slot.close();h.run()
    }}}

    @Test fun detachDuringSignedResolutionCannotAttachCandidate(){Fixture().use{f->
        f.activate();val h=CaptureHarness();var checks=0
        val ticket=h.slot.prepare(h.e,h.c,h.c.token()!!,{checks++;if(checks==3)h.slot.detach();true})!!
        assertFalse(h.install(f,ticket));assertEquals(0,h.vc);assertEquals(0,h.ac)
        assertTrue(h.install(f));h.slot.close();h.run()
    }}

}
