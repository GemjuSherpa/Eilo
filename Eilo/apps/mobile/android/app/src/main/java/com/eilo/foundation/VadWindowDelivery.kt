package com.eilo.foundation

internal data class VadDeliveryEvent(val result: EndpointResult, val consumedSamples: Int)

/** Single inference-worker owner. Capture callbacks enqueue/copy elsewhere; no caller pointer,
 * controller lock, scheduling or unbounded queue is owned here. */
internal class VadWindowDelivery(private val allowed: () -> Boolean = { false },
    private val open: () -> VadStream = { error("VAD unavailable") }) {
    private val endpoint = NativeVadEndpointBridge(allowed)
    private var stream: VadStream? = null
    private val scratch = FloatArray(512)
    private var pending = 0
    private var inputSamples = 0
    private var closed = false
    private fun valid() = try { allowed() } catch (_: Exception) { false }
    fun retainedSamples() = pending
    fun acceptedSamples() = inputSamples
    private fun clear() { scratch.fill(0f); pending = 0 }
    private fun invalid(): VadDeliveryEvent { close(); return VadDeliveryEvent(EndpointResult.INVALID, 0) }

    fun accept(pcm: FloatArray, count: Int, startSample: Int): VadDeliveryEvent {
        if (closed || !valid() || startSample != inputSamples || count !in 1..1600 || count > pcm.size ||
            (0 until count).any { !pcm[it].isFinite() || pcm[it] !in -1f..1f }) return invalid()
        var offset = 0
        while (offset < count) {
            val capacity = endpoint.inputCapacity()
            if (!valid() || capacity <= pending) return invalid()
            val take = minOf(capacity-pending, count-offset)
            pcm.copyInto(scratch, pending, offset, offset+take)
            pending += take; inputSamples += take; offset += take
            if (!valid()) return invalid()
            if (pending == capacity) {
                val result = process(capacity < 512) ?: return invalid()
                if (result != EndpointResult.CONTINUE) return finishEvent(result, offset)
            }
        }
        if (!valid()) return invalid()
        return VadDeliveryEvent(EndpointResult.CONTINUE, offset)
    }
    fun finish(): VadDeliveryEvent {
        if (closed || !valid()) return invalid()
        if (pending == 0) return finishEvent(EndpointResult.INCOMPLETE, 0)
        return finishEvent(process(true) ?: return invalid(), 0)
    }
    private fun process(final: Boolean): EndpointResult? {
        try {
            if (!valid()) return null
            if (stream == null) {
                val candidate = open()
                if (!valid()) { candidate.close(); return null }
                stream = candidate
            }
            val current = stream ?: return null
            if (!valid()) return null
            val expected = pending
            val start = endpoint.elapsedSamples()
            val frame = current.process(scratch, expected, final)
            if (closed || !valid() || frame.startSample != start || frame.samples != expected || frame.final != final) return null
            return endpoint.consume(frame)
        } catch (_: Exception) { return null }
        finally { clear() }
    }
    private fun finishEvent(result: EndpointResult, consumed: Int): VadDeliveryEvent {
        close()
        if (!valid() || result == EndpointResult.CONTINUE) return VadDeliveryEvent(EndpointResult.INVALID, 0)
        return VadDeliveryEvent(result, if (result == EndpointResult.INVALID) 0 else consumed)
    }
    fun close() {
        if (closed) return
        closed = true
        val previous = stream; stream = null
        clear(); endpoint.close()
        try { previous?.close() } catch (_: Exception) { /* revoked, never revive */ }
    }
}
