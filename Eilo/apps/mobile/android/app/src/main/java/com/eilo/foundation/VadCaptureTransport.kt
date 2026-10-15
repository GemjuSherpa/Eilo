package com.eilo.foundation

import java.util.concurrent.Executor

internal data class VadCaptureOutcome(val result: EndpointResult, val totalSamples: Int, val lastChunkConsumed: Int)

/** Four copied <=100 ms frames, <250 ms queue age, one coalesced job. Worker MUST be a
 * dedicated serial inference executor, never inline/the recorder executor. verified is disk-free
 * and must not acquire capture/controller monitors. Stop signals; only the worker destroys state. */
internal class VadCaptureTransport(
    private val worker: Executor,
    private val verified: () -> Boolean = { false },
    private val open: () -> VadStream = { error("VAD unavailable") },
    private val now: () -> Long = System::nanoTime,
    private val failure: (() -> Boolean) -> Unit = {},
    private val output: (VadCaptureOutcome, () -> Boolean) -> Unit = { _, _ -> },
) {
    private val monitor=Any()
    private val storage=FloatArray(6400)
    private val counts=IntArray(4)
    private val times=LongArray(4)
    private var head=0; private var size=0; private var queuedSamples=0
    private var accepting=true; private var active=true; private var scheduled=false; private var eof=false
    private var failed=false
    private var lastClock: Long?=null
    // Worker-confined fields.
    private var delivery: VadWindowDelivery?=null
    private val scratch=FloatArray(1600)
    fun retainedSamples()=synchronized(monitor) { queuedSamples }
    fun current()=synchronized(monitor) { active }
    private fun allowed()=try { current() && verified() && current() } catch (_: Exception) { false }
    private fun clearLocked() { storage.fill(0f);counts.fill(0);times.fill(0);head=0;size=0;queuedSamples=0 }
    private fun revokeLocked() { failed=true;active=false;accepting=false;clearLocked() }
    private fun claimLocked():Boolean { if(scheduled)return false;scheduled=true;return true }
    private fun enqueue(start:Boolean) { if(start) worker.execute(::drain) }
    fun submit(pcm:FloatArray,count:Int,sampleRate:Int):Boolean {
        val valid:Boolean;val start:Boolean
        synchronized(monitor) {
            if(!accepting)return false
            val time=now()
            valid=sampleRate==16000 && count in 1..1600 && count<=pcm.size && size<4 &&
                (0 until count).all { pcm[it].isFinite() && pcm[it] in -1f..1f } &&
                (lastClock==null || time>=lastClock!!) &&
                (size==0 || (time>=times[head] && time-times[head]<250_000_000))
            if(valid) {
                val slot=(head+size)%4;pcm.copyInto(storage,slot*1600,0,count)
                counts[slot]=count;times[slot]=time;size++;queuedSamples+=count;lastClock=time
            } else revokeLocked()
            start=claimLocked()
        }
        enqueue(start);return valid
    }
    /** Recorder's PCM16 is copied/converted without allocating or invoking inference. */
    fun submit(pcm:ShortArray,count:Int,sampleRate:Int):Boolean {
        val start:Boolean;val valid:Boolean
        synchronized(monitor) {
            if(!accepting)return false
            val time=now()
            valid=sampleRate==16000 && count in 1..1600 && count<=pcm.size && size<4 &&
                (lastClock==null || time>=lastClock!!) &&
                (size==0 || (time>=times[head] && time-times[head]<250_000_000))
            if(valid) {
                val slot=(head+size)%4
                for(i in 0 until count)storage[slot*1600+i]=pcm[i]/32768f
                counts[slot]=count;times[slot]=time;size++;queuedSamples+=count;lastClock=time
            } else revokeLocked()
            start=claimLocked()
        }
        enqueue(start);return valid
    }
    fun finish() {
        val start=synchronized(monitor) { if(!accepting)return;accepting=false;eof=true;claimLocked() }
        enqueue(start)
    }
    fun close() {
        val start=synchronized(monitor) { revokeLocked();failed=false;claimLocked() }
        enqueue(start)
    }
    private fun drain() {
        while(true) {
            var count=0;var final=false;var revoked=false
            synchronized(monitor) {
                if(!active) { clearLocked();revoked=true }
                else if(size==0) { if(!eof) { scheduled=false;return };final=true }
                else {
                    val time=now()
                    if(time<times[head] || time-times[head]>=250_000_000 || (lastClock!=null && time<lastClock!!)) {
                        revokeLocked();revoked=true
                    } else {
                        lastClock=time;count=counts[head];val offset=head*1600
                        storage.copyInto(scratch,0,offset,offset+count);storage.fill(0f,offset,offset+count)
                        counts[head]=0;times[head]=0;head=(head+1)%4;size--;queuedSamples-=count
                    }
                }
            }
            if(revoked) { cleanup();synchronized(monitor) { scheduled=false };reportFailure();return }
            val current=delivery ?: VadWindowDelivery(::allowed,open).also { delivery=it }
            val event=if(final)current.finish() else current.accept(scratch,count,current.acceptedSamples())
            scratch.fill(0f)
            if(event.result!=EndpointResult.CONTINUE) { complete(event);return }
        }
    }
    private fun complete(event:VadDeliveryEvent) {
        val outcome=VadCaptureOutcome(event.result,delivery?.acceptedSamples() ?: 0,event.consumedSamples)
        cleanup()
        synchronized(monitor) { accepting=false;clearLocked();scheduled=false;if(event.result==EndpointResult.INVALID){if(active)failed=true;active=false} }
        if(event.result==EndpointResult.INVALID)reportFailure() else if(allowed())output(outcome,::allowed)
    }
    private fun failureCurrent()=synchronized(monitor) { failed }
    private fun reportFailure() { if(failureCurrent())failure(::failureCurrent) }
    private fun cleanup() { scratch.fill(0f);delivery?.close();delivery=null }
}
