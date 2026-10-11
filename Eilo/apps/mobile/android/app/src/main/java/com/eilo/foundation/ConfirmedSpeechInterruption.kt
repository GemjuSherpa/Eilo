package com.eilo.foundation

/** Native-worker VAD evidence, not raw energy or an ASR transcript. App playback must already
 * be separated by a verified native route. Defaults cannot supply that independent evidence. */
internal class ConfirmedSpeechInterruption(private val token:GenerationToken) {
    private var high=0
    private var closed=false
    fun advance(probability:Float,independentUserSpeech:Boolean,samples:Int=320):InterruptionActivation? {
        if(closed || token.cancelled)return null
        if(samples!=320 || !probability.isFinite() || probability !in 0f..1f){closed=true;high=0;return null}
        if(!independentUserSpeech || probability<.8f){high=0;return null}
        high+=samples
        if(high<2560)return null
        closed=true;high=0;return InterruptionActivation(token)
    }
}
internal class InterruptionActivation(private val token:GenerationToken) {
    fun apply(controller:NativeController,independentSpeechStillVerified:()->Boolean):GenerationToken? =
        controller.interruptReply(token,independentSpeechStillVerified)
}
