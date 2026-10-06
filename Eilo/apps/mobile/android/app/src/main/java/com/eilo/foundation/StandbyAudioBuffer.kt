package com.eilo.foundation

/** Native volatile mono PCM16. No storage, ASR, bridge or model consumer. */
internal class StandbyAudioBuffer(private val sampleRate:Int=16000,private val now:()->Long=System::nanoTime) {
    init { require(sampleRate in 8000..192000) }
    private val samples=ShortArray(sampleRate*2)
    private val receivedAt=LongArray(samples.size)
    private var head=0;private var size=0;private var epoch=0L;private var open=false
    private var lastClock:Long?=null
    @Synchronized fun begin():Long { clear();epoch++;open=true;return epoch }
    @Synchronized fun close() { open=false;epoch++;clear() }
    @Synchronized fun clear() { samples.fill(0);receivedAt.fill(0);head=0;size=0;lastClock=null }
    @Synchronized fun expire() {
        val time=now();val previous=lastClock
        if(previous!=null && time-previous<0) clear() // Broken/regressing clock fails closed.
        lastClock=time
        while(size>0 && time-receivedAt[head]>=2_000_000_000L) {
            samples[head]=0;receivedAt[head]=0;head=(head+1)%samples.size;size--
        }
    }
    @Synchronized fun append(ticket:Long,input:ShortArray,count:Int) {
        require(count in 0..input.size)
        if(!open || ticket!=epoch) return
        expire();val time=now()
        // Keep the suffix of a large frame without transient growth.
        for(i in maxOf(0,count-samples.size) until count) {
            if(size==samples.size) { samples[head]=0;receivedAt[head]=0;head=(head+1)%samples.size;size-- }
            val slot=(head+size)%samples.size;samples[slot]=input[i];receivedAt[slot]=time;size++
        }
    }
    @Synchronized fun count():Int { expire();return size }
    // Internal scalar inspection only; no PCM array snapshot or consumer is exported.
    @Synchronized fun sample(index:Int):Short { expire();require(index in 0 until size);return samples[(head+index)%samples.size] }
}
