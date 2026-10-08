package com.eilo.foundation

/** Native verified-pack paths only; never accepted from JavaScript. */
internal data class WakeModelPaths(val encoder:String,val decoder:String,val joiner:String,val tokens:String) {
    init { require(listOf(encoder,decoder,joiner,tokens).all {
        it.startsWith("/") && !it.contains('\u0000') && it.toByteArray(Charsets.UTF_8).size <= 4096
    }) }
}

/** An unavailable default keeps linking separate from model readiness and permission. */
internal interface NativeWakeAPI {
    fun create(paths:WakeModelPaths,configuration:WakeConfiguration):Long
    fun process(handle:Long,samples:FloatArray,count:Int,rate:Int):Int
    fun destroy(handle:Long)
    companion object {
        val unavailable=object:NativeWakeAPI {
            override fun create(paths:WakeModelPaths,configuration:WakeConfiguration)=0L
            override fun process(handle:Long,samples:FloatArray,count:Int,rate:Int)=-1
            override fun destroy(handle:Long) {}
        }
    }
}

/** JNI has no automatic loader and is not exposed by a TurboModule. Local evaluation loads it explicitly. */
internal object NativeWakeJNI:NativeWakeAPI {
    private external fun createNative(encoder:String,decoder:String,joiner:String,tokens:String,threshold:Float,boost:Float):Long
    private external fun processNative(handle:Long,samples:FloatArray,count:Int,rate:Int):Int
    private external fun destroyNative(handle:Long)
    override fun create(paths:WakeModelPaths,configuration:WakeConfiguration)=
        try { createNative(paths.encoder,paths.decoder,paths.joiner,paths.tokens,configuration.threshold,configuration.boost) }
        catch (_:UnsatisfiedLinkError) { 0L }
    override fun process(handle:Long,samples:FloatArray,count:Int,rate:Int)=
        try { processNative(handle,samples,count,rate) } catch (_:UnsatisfiedLinkError) { -1 }
    override fun destroy(handle:Long) {
        try { destroyNative(handle) } catch (_:UnsatisfiedLinkError) { error("unavailable") }
    }
}

/** Serialized worker binding. C++ decodes/resets; this layer returns the fixed keyword only. */
internal class NativeWakeStream(
    paths:WakeModelPaths,configuration:WakeConfiguration,
    private val verified:()->Boolean,private val api:NativeWakeAPI=NativeWakeAPI.unavailable,
):WakeKeywordStream {
    private var handle=0L
    private var matched=false
    private var sampleRate:Int?=null
    init {
        check(configuration.phrase=="HEY EILO" && verified())
        val candidate=api.create(paths,configuration)
        check(candidate>0L)
        // Every created handle must be released even if verification throws during opening.
        try { check(verified());handle=candidate } catch (failure:Exception) { api.destroy(candidate);throw failure }
    }
    @Synchronized override fun accept(samples:FloatArray,count:Int,sampleRate:Int) {
        try {
            check(handle!=0L && verified() && sampleRate in 8000..192000 && count in 1..samples.size && count<=sampleRate/10)
            check(this.sampleRate==null || this.sampleRate==sampleRate)
            for(i in 0 until count) check(samples[i].isFinite() && samples[i] in -1f..1f)
            this.sampleRate=sampleRate
            val result=api.process(handle,samples,count,sampleRate)
            check((result==0 || result==1) && verified())
            matched=matched || result==1
        } catch (failure:Exception) { close();throw failure }
    }
    @Synchronized override fun ready():Boolean { checkActive();return false }
    override fun decode() { error("unavailable") } // Already decoded synchronously in C++ accept.
    @Synchronized override fun keyword():String { checkActive();return if(matched) "HEY EILO" else "" }
    @Synchronized override fun reset() { checkActive();matched=false }
    private fun checkActive() {
        try { check(handle!=0L && verified()) } catch (failure:Exception) { close();throw failure }
    }
    @Synchronized override fun close() {
        val previous=handle;handle=0L;matched=false;sampleRate=null
        if(previous!=0L) api.destroy(previous)
    }
}
