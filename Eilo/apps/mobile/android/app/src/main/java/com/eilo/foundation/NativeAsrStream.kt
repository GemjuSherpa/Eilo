package com.eilo.foundation

import java.nio.ByteBuffer
import java.nio.charset.CodingErrorAction

internal interface NativeAsrApi {
    fun create(directory:String):Long
    fun accept(handle:Long,pcm:FloatArray,count:Int):Int
    fun text(handle:Long,finish:Boolean):ByteArray?
    fun destroy(handle:Long)
}
internal object UnavailableAsrApi:NativeAsrApi {
    override fun create(directory:String)=0L
    override fun accept(handle:Long,pcm:FloatArray,count:Int)=-1
    override fun text(handle:Long,finish:Boolean):ByteArray?=null
    override fun destroy(handle:Long){}
}

/** Explicit evaluation loading only. Caller verifies exact immutable files before loading.
 * This imports no SDK microphone, downloader, network client or bridge API. */
internal object NativeAsrJni {
    private external fun create(path:ByteArray):Long
    external fun accept(handle:Long,pcm:FloatArray,count:Int):Int
    external fun read(handle:Long,finish:Boolean):ByteArray?
    external fun destroy(handle:Long)
    fun loadVerified(libraries:List<String>,verified:()->Boolean):NativeAsrApi {
        require(verified() && libraries.size==3 && libraries.all{it.startsWith('/') && !it.contains('\u0000')})
        libraries.forEach { System.load(it) }
        require(verified())
        return object:NativeAsrApi {
            override fun create(directory:String)=NativeAsrJni.create(directory.toByteArray(Charsets.UTF_8))
            override fun accept(handle:Long,pcm:FloatArray,count:Int)=NativeAsrJni.accept(handle,pcm,count)
            override fun text(handle:Long,finish:Boolean)=NativeAsrJni.read(handle,finish)
            override fun destroy(handle:Long)=NativeAsrJni.destroy(handle)
        }
    }
}

/** Inference-worker confined: handles never cross JS and Stop never waits under controller lock. */
internal class NativeAsrStream(directory:String,private val verified:()->Boolean,
    private val api:NativeAsrApi=UnavailableAsrApi):AsrStream {
    private var handle=0L
    private fun validLease()=try{verified()}catch(_:Exception){false}
    init {
        require(directory.startsWith('/') && directory.toByteArray(Charsets.UTF_8).size<=4096 && !directory.contains('\u0000') && validLease())
        val candidate=api.create(directory)
        check(candidate>0)
        if(!validLease()){api.destroy(candidate);error("ASR unavailable")}
        handle=candidate
    }
    override fun accept(pcm:FloatArray,count:Int) {
        if(handle<=0 || !validLease() || count !in 1..1600 || count>pcm.size || (0 until count).any{!pcm[it].isFinite() || pcm[it] !in -1f..1f} || api.accept(handle,pcm,count)!=0 || !validLease()) {
            close();error("ASR unavailable")
        }
    }
    override fun text(finish:Boolean):String {
        var bytes:ByteArray?=null
        try {
            check(handle>0 && validLease())
            bytes=api.text(handle,finish);check(bytes!=null && bytes.size<=4096 && validLease())
            return Charsets.UTF_8.newDecoder().onMalformedInput(CodingErrorAction.REPORT)
                .onUnmappableCharacter(CodingErrorAction.REPORT).decode(ByteBuffer.wrap(bytes)).toString()
        } catch (_:Exception){close();error("ASR unavailable")}
        finally{bytes?.fill(0)}
    }
    override fun close(){val previous=handle;handle=0;if(previous>0)api.destroy(previous)}
}
