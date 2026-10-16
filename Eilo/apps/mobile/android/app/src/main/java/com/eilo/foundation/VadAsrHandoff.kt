package com.eilo.foundation

internal sealed interface VadAsrFinal {
    data object Metadata:VadAsrFinal
    data class Recognized(val text:AsrText):VadAsrFinal
    data object Invalid:VadAsrFinal
}

/** One native worker's <=30 s 16 kHz utterance. Only exact VAD-consumed prefixes are retained.
 * Silence/early EOF never opens ASR. No file/JS/log consumer or confidence inference. */
internal class VadAsrHandoff(private val token:GenerationToken,private val allowed:()->Boolean,
    private val open:()->AsrStream) {
    private val pcm=FloatArray(480000)
    private var count=0;private var closed=false
    fun retainedSamples()=count
    private fun valid()=!closed && !token.cancelled && try{allowed()}catch(_:Exception){false}
    fun append(input:FloatArray,inputCount:Int,consumed:Int,startSample:Int):Boolean {
        if(!valid() || startSample!=count || inputCount !in 1..1600 || inputCount>input.size || consumed !in 1..inputCount ||
            count>480000-consumed || (0 until inputCount).any{!input[it].isFinite() || input[it] !in -1f..1f}){close();return false}
        input.copyInto(pcm,count,0,consumed);count+=consumed
        if(!valid()){close();return false};return true
    }
    fun finish(outcome:VadCaptureOutcome):VadAsrFinal {
        try {
            if(!valid() || outcome.totalSamples!=count || outcome.lastChunkConsumed !in 0..1600)return VadAsrFinal.Invalid
            when(outcome.result) {
                EndpointResult.NO_SPEECH->return if(count==80000)VadAsrFinal.Metadata else VadAsrFinal.Invalid
                EndpointResult.INCOMPLETE->return VadAsrFinal.Metadata
                EndpointResult.COMPLETE,EndpointResult.LIMIT->if(count==0 || (outcome.result==EndpointResult.LIMIT && count!=480000))return VadAsrFinal.Invalid
                else->return VadAsrFinal.Invalid
            }
            val asr=StreamingAsr(token,allowed,open)
            try {
                var offset=0
                val scratch=FloatArray(1600)
                try {
                    while(offset<count) {
                        val n=minOf(1600,count-offset);pcm.copyInto(scratch,0,offset,offset+n)
                        if(!valid() || !asr.accept(scratch,n))return VadAsrFinal.Invalid
                        scratch.fill(0f);offset+=n
                    }
                } finally {scratch.fill(0f)}
                if(!valid())return VadAsrFinal.Invalid
                val text=asr.poll(true) ?: return VadAsrFinal.Invalid
                return if(valid() && text.final)VadAsrFinal.Recognized(text) else VadAsrFinal.Invalid
            } finally {asr.close()}
        } finally {close()}
    }
    fun close(){if(closed)return;closed=true;pcm.fill(0f);count=0}
}
