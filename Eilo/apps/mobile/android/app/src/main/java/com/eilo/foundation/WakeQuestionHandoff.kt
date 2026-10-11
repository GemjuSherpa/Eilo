package com.eilo.foundation

/** Native 16 kHz sequence-addressed suffix. No disk/bridge and no ASR before activation.
 * Worker-owned: borrowed sink input is erased after every call. Close on Stop/privacy/route change.
 */
internal class WakeQuestionHandoff {
    private val ring=ShortArray(32000)
    private val scratch=ShortArray(32000)
    private var head=0;private var size=0;private var next=0L;private var initialized=false
    private var token:GenerationToken?=null
    private var valid:()->Boolean={false}
    private var sink:((ShortArray,Int)->Unit)?=null
    private var active=false;private var closed=false
    @Synchronized fun offer(input:ShortArray,count:Int,startSample:Long):Boolean {
        if(closed || count !in 1..input.size || count>1600 || startSample<0 || startSample>Long.MAX_VALUE-count) { close();return false }
        if(initialized && startSample>next) { close();return false } // Gaps fail closed.
        if(!initialized) { next=startSample;initialized=true }
        val skip=(next-startSample).coerceAtLeast(0).coerceAtMost(count.toLong()).toInt()
        if(skip==count)return true // Already delivered overlap never repeats.
        if(active) {
            val expected=token
            if(expected==null || expected.cancelled || !valid()) { close();return false }
            val n=count-skip
            input.copyInto(scratch,0,skip,count)
            try { sink!!(scratch,n);if(expected.cancelled || !valid()){close();return false} }
            catch(_:Exception){close();return false} finally {scratch.fill(0)}
        } else {
            for(i in skip until count) {
                if(size==ring.size){ring[head]=0;head=(head+1)%ring.size;size--}
                ring[(head+size)%ring.size]=input[i];size++
            }
        }
        next=startSample+count
        return true
    }
    /** firstQuestionSample is a native decoder boundary; retain full bounded suffix if unavailable.
     * Activation must already be accepted by the controller. Rechecks are disk-free/lock-free.
     */
    @Synchronized fun activate(expected:GenerationToken,firstQuestionSample:Long?,allowed:()->Boolean,consume:(ShortArray,Int)->Unit):Boolean {
        if(closed || active || expected.cancelled || !allowed() || !initialized)return false
        val oldest=next-size
        val first=firstQuestionSample ?: oldest
        if(first !in oldest..next) {close();return false}
        val skip=(first-oldest).toInt();val n=size-skip
        for(i in 0 until n)scratch[i]=ring[(head+skip+i)%ring.size]
        ring.fill(0);head=0;size=0
        token=expected;valid=allowed;sink=consume;active=true
        try { if(n>0)consume(scratch,n);if(expected.cancelled || !allowed()){close();return false};return true }
        catch(_:Exception){close();return false} finally {scratch.fill(0)}
    }
    @Synchronized fun close(){closed=true;active=false;token=null;sink=null;valid={false};ring.fill(0);scratch.fill(0);head=0;size=0}
    @Synchronized fun retainedSamples()=size
}
