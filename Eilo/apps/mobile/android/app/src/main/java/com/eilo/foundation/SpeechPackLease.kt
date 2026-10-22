package com.eilo.foundation

import java.io.File
import java.util.UUID

internal enum class SpeechPackKind { VAD,ASR }
internal data class SpeechArtifactPin(val id:String,val filename:String,val sha256:String,val bytes:Long,val licenseEvidence:String) {
    init {
        require(id.matches(Regex("[a-z0-9][a-z0-9-]{0,63}")) && sha256.matches(Regex("[a-f0-9]{64}")) && licenseEvidence.matches(Regex("[a-f0-9]{64}")))
        require(bytes in 1..8_000_000_000L && (PackManifest.validFilename(filename,"asr") || PackManifest.validFilename(filename,"tokenizer") || PackManifest.validFilename(filename,"vad")))
    }
}
/** Reviewed native pins, never inferred from manifest order or supplied by JS. */
internal class SpeechPackSelection(val packId:String,val runtimeRevision:String,val kind:SpeechPackKind,pins:List<SpeechArtifactPin>) {
    val pins:List<SpeechArtifactPin> = java.util.Collections.unmodifiableList(pins.toList())
    init {
        require(packId.matches(Regex("[a-z0-9][a-z0-9-]{0,63}")) && runtimeRevision.matches(Regex("[a-f0-9]{40}")))
        require(this.pins.map{it.id}.toSet().size==this.pins.size && this.pins.map{it.filename}.toSet().size==this.pins.size)
        when(kind){SpeechPackKind.VAD->require(this.pins.size==1 && (this.pins[0].filename.endsWith(".onnx") || this.pins[0].filename=="silero_vad_v5.ort"));SpeechPackKind.ASR->require(this.pins.map{it.filename}.toSet()==asrNames)}
    }
    companion object {val asrNames:Set<String> = java.util.Collections.unmodifiableSet(setOf("adapter.ort","cross_kv.ort","decoder_kv.ort","encoder.ort","frontend.model.ort","frontend.weights.ort","streaming_config.json","tokenizer.bin"))}
}

/** Resolve on installer/inference worker; subsequent checks are disk-free epochs. Slots must
 * stay app-private/immutable; revoke before maintenance. Worker owns native destruction/join. */
internal class SpeechPackLease private constructor(private val store:PackStore,private val epoch:UUID,
    private val kind:SpeechPackKind,private val paths:List<File>) {
    @Volatile private var active=true
    fun verified()=active && store.epoch()==epoch
    fun close(){active=false}
    fun openVad(allowed:()->Boolean,api:NativeVadApi=UnavailableVadApi):NativeVadStream {
        check(kind==SpeechPackKind.VAD && verified() && allowed())
        return NativeVadStream(paths[0].absolutePath,{verified() && allowed()},api)
    }
    fun openAsr(allowed:()->Boolean,api:NativeAsrApi=UnavailableAsrApi):NativeAsrStream {
        check(kind==SpeechPackKind.ASR && verified() && allowed())
        return NativeAsrStream(paths[0].parentFile!!.absolutePath,{verified() && allowed()},api)
    }
    companion object {
        fun resolve(store:PackStore,selection:SpeechPackSelection):SpeechPackLease {
            try {
                val epoch=store.epoch();val snapshot=store.verifiedFiles() ?: error("unavailable")
                val manifest=snapshot.first.manifest
                check(manifest.packId==selection.packId && manifest.runtimeRevision==selection.runtimeRevision)
                val paths=selection.pins.map{pin->
                    val index=manifest.artifacts.indexOfFirst{it.id==pin.id};check(index>=0)
                    val artifact=manifest.artifacts[index]
                    val role=if(selection.kind==SpeechPackKind.VAD)"vad" else if(pin.filename=="tokenizer.bin")"tokenizer" else "asr"
                    check(artifact.filename==pin.filename && artifact.role==role && artifact.sha256==pin.sha256 && artifact.bytes==pin.bytes && artifact.license=="MIT" && artifact.licenseEvidence==pin.licenseEvidence)
                    snapshot.second[index]
                }
                check(store.epoch()==epoch && paths.isNotEmpty() && paths.map{it.parentFile}.toSet().size==1)
                return SpeechPackLease(store,epoch,selection.kind,paths)
            }catch(_:Exception){error("speech pack unavailable")}
        }
    }
}
