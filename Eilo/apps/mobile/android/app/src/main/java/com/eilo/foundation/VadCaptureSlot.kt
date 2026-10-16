package com.eilo.foundation

import java.util.concurrent.Executor

internal class VadCapturePermit {
    private val monitor=Any()
    private var valid=true
    var cancel:()->Unit={}
    fun active()=synchronized(monitor){valid}
    fun revoke() { val notify=synchronized(monitor){val previous=valid;valid=false;previous};if(notify)cancel() }
}

/** Capture-run slot. Stop closes forever; detach invalidates pending setup epochs. */
internal class VadCaptureSlot(val sampleRate:Int) {
    private val monitor=Any()
    private var live=true;private var epoch=0L
    private var binding:Pair<VadCapturePermit,VadCaptureTransport>?=null
    /** Explicit native-worker setup; normal app never calls it or loads a default VAD runtime. */
    fun install(capture:ControllerEffects,controller:NativeController,token:GenerationToken,worker:Executor,
        verified:()->Boolean={false},open:((()->Boolean))->VadStream={error("VAD unavailable")},
        accepted:(VadCaptureOutcome)->Unit={},openAsr:((()->Boolean)->AsrStream)?=null,
        recognized:(AsrText)->Unit={},asrVerified:()->Boolean={false}):Boolean {
        val verifiedNow={try { verified() && (openAsr==null || asrVerified()) } catch (_:Exception){false}}
        if(sampleRate !in listOf(16000,48000) || !verifiedNow() || token.cancelled)return false
        val ticket=synchronized(monitor){if(!live || binding!=null)return false;epoch}
        val permit=VadCapturePermit()
        val check={permit.active() && !token.cancelled && verifiedNow()}
        val audioFactory:(()->VadAsrHandoff)?=openAsr?.let{factory->{VadAsrHandoff(token,check,{factory(check)})}}
        val joined:((VadCaptureOutcome,AsrText?,()->Boolean)->Unit)?=if(audioFactory==null)null else {outcome,text,current->
            try {controller.finishVadCapture(permit,token,outcome,current){value->if(text!=null)recognized(text);if(current())accepted(value)}}
            catch(_:Exception){controller.dispatch(ControllerEvent.FAILURE,SafeError.UNAVAILABLE,token)}
            finally {retire(permit)}
        }
        val transport=VadCaptureTransport(worker,check,{open(check)},failure={current->
            try { controller.failVadCapture(permit,token,current) } finally { retire(permit) }
        },output={outcome,current->
            try { controller.finishVadCapture(permit,token,outcome,current,accepted) } finally { retire(permit) }
        },audioFactory=audioFactory,joinedOutput=joined,sourceRate=sampleRate)
        permit.cancel={transport.close()}
        if(!controller.prepareVadCapture(permit,capture,token)){transport.close();return false}
        val stillVerified=check()
        val attached=synchronized(monitor){
            if(!stillVerified || !live || epoch!=ticket || binding!=null || !permit.active() || token.cancelled)false
            else {binding=permit to transport;epoch++;true}
        }
        if(!attached){controller.abandonVadCapture(permit);transport.close()}
        return attached
    }
    fun submit(pcm:ShortArray,count:Int,sampleRate:Int) {
        val current=synchronized(monitor){if(live)binding?.second else null}
        current?.submit(pcm,count,sampleRate)
    }
    fun finish(){val current=synchronized(monitor){binding?.second};current?.finish()}
    private fun retire(permit:VadCapturePermit) {
        val previous=synchronized(monitor){if(binding?.first!==permit)null else binding.also{binding=null;epoch++}}
        previous?.first?.revoke()
    }
    fun detach(){val previous=synchronized(monitor){binding.also{binding=null;epoch++}};previous?.first?.revoke();previous?.second?.close()}
    fun close(){synchronized(monitor){live=false};detach()}
}
