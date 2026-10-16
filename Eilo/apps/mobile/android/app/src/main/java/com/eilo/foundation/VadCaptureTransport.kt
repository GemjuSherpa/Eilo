package com.eilo.foundation

import java.util.concurrent.Executor

/** Normalized 16 kHz counts, never source-frame indices. */
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
    private val audioFactory:(()->VadAsrHandoff)?=null,
    private val joinedOutput:((VadCaptureOutcome,AsrText?,()->Boolean)->Unit)?=null,
    private val sourceRate:Int=16000,
) {
    private val monitor=Any()
    private val frameCapacity=if(sourceRate==48000)4800 else 1600
    private val storage=FloatArray(frameCapacity*4)
    private var converter:StreamingRateConverter?=null
    private val counts=IntArray(4)
    private val times=LongArray(4)
    private var head=0; private var size=0; private var queuedSamples=0
    private var accepting=true; private var active=true; private var scheduled=false; private var eof=false
    private var failed=false
    private var lastClock: Long?=null
    // Worker-confined fields.
    private var audio:VadAsrHandoff?=null
    private var delivery: VadWindowDelivery?=null
    private val scratch=FloatArray(frameCapacity)
    /** Queued raw source samples; worker-owned state is separate. */
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
            valid=(sourceRate==16000 || sourceRate==48000) && sampleRate==sourceRate && count in 1..frameCapacity && count<=pcm.size && size<4 &&
                (0 until count).all { pcm[it].isFinite() && pcm[it] in -1f..1f } &&
                (lastClock==null || time>=lastClock!!) &&
                (size==0 || (time>=times[head] && time-times[head]<250_000_000))
            if(valid) {
                val slot=(head+size)%4;pcm.copyInto(storage,slot*frameCapacity,0,count)
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
            valid=(sourceRate==16000 || sourceRate==48000) && sampleRate==sourceRate && count in 1..frameCapacity && count<=pcm.size && size<4 &&
                (lastClock==null || time>=lastClock!!) &&
                (size==0 || (time>=times[head] && time-times[head]<250_000_000))
            if(valid) {
                val slot=(head+size)%4
                for(i in 0 until count)storage[slot*frameCapacity+i]=pcm[i]/32768f
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
                        lastClock=time;count=counts[head];val offset=head*frameCapacity
                        storage.copyInto(scratch,0,offset,offset+count);storage.fill(0f,offset,offset+count)
                        counts[head]=0;times[head]=0;head=(head+1)%4;size--;queuedSamples-=count
                    }
                }
            }
            if(revoked) { cleanup();synchronized(monitor) { scheduled=false };reportFailure();return }
            val current=delivery ?: VadWindowDelivery(::allowed,open).also { delivery=it }
            var event=VadDeliveryEvent(EndpointResult.CONTINUE,0)
            if(final)event=current.finish() else try {
                check(allowed())
                val rate=converter ?: StreamingRateConverter(sourceRate).also{converter=it}
                rate.convert(scratch,count){normalized,n->
                    check(allowed());event=current.accept(normalized,n,current.acceptedSamples())
                    if(event.result!=EndpointResult.INVALID && allowed() && audioFactory!=null) {
                        val owned=audio ?: audioFactory.invoke().also{audio=it}
                        check(owned.append(normalized,n,event.consumedSamples,current.acceptedSamples()-event.consumedSamples))
                    }
                }
                check(allowed())
            } catch(_:Exception){event=VadDeliveryEvent(EndpointResult.INVALID,0)}
            scratch.fill(0f)
            if(event.result!=EndpointResult.CONTINUE) { complete(event);return }
        }
    }
    private fun complete(event:VadDeliveryEvent) {
        val outcome=VadCaptureOutcome(event.result,delivery?.acceptedSamples() ?: 0,event.consumedSamples)
        var text:AsrText?=null;var invalid=event.result==EndpointResult.INVALID
        if(!invalid && audioFactory!=null) {
            val owned=audio ?: audioFactory.invoke().also{audio=it}
            when(val final=owned.finish(outcome)) {
                VadAsrFinal.Metadata->Unit
                VadAsrFinal.Invalid->invalid=true
                is VadAsrFinal.Recognized->text=final.text
            }
        }
        cleanup()
        synchronized(monitor) { accepting=false;clearLocked();scheduled=false;if(invalid){if(active)failed=true;active=false} }
        if(invalid)reportFailure() else if(allowed()) {
            if(joinedOutput!=null)joinedOutput.invoke(outcome,text,::allowed) else output(outcome,::allowed)
        }
    }
    private fun failureCurrent()=synchronized(monitor) { failed }
    private fun reportFailure() { if(failureCurrent())failure(::failureCurrent) }
    private fun cleanup() { scratch.fill(0f);delivery?.close();delivery=null;audio?.close();audio=null;converter?.close();converter=null }
}
