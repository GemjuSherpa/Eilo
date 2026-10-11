package com.eilo.foundation

/** Conservative speaker/headphone fallback: reject known app output plus300 ms acoustic tail.
 * Full duplex requires separately verified echo separation. Metadata only, no PCM/text. */
internal class PlaybackRejection(private val now:()->Long) {
    private var output:GenerationToken?=null
    private var until=0L
    private var previous:Long?=null
    private var invalidClock=false
    @Synchronized fun begin(token:GenerationToken){if(!token.cancelled)output=token}
    @Synchronized fun finish(token:GenerationToken):Boolean {
        if(output!==token)return false
        cancel();return true
    }
    @Synchronized fun cancel(){if(output!=null){output=null;val t=time();until=if(t>Long.MAX_VALUE-300)Long.MAX_VALUE else t+300}}
    private fun time():Long {
        val t=try{now()}catch(_:Exception){invalidClock=true;0L}
        if(t<0 || previous?.let{t<it}==true)invalidClock=true
        previous=t;return t
    }
    @Synchronized fun allowsAudio():Boolean{val t=time();return !invalidClock && output==null && t>=until}
}
