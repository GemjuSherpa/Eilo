package com.eilo.foundation

internal enum class EndpointResult { CONTINUE, COMPLETE, NO_SPEECH, LIMIT, INCOMPLETE, INVALID }

/** Worker-confined sample clock. Never duplicate a native window score into 20 ms frames. */
internal class EndpointDetector {
    private var total = 0
    private var high = 0
    private var quiet = 0
    private var speech = false
    private var terminal = false
    private var nativeMode: Boolean? = null

    fun advance(probability: Float, samples: Int = 320): EndpointResult {
        if (terminal || nativeMode == true || samples != 320) return invalidate()
        nativeMode = false
        return consume(probability, samples, false)
    }

    fun nativeInputCapacity(): Int = if (terminal || nativeMode == false) 0
        else minOf(512, (if (speech) 480000 else 80000) - total)

    fun advanceNative(probability: Float, startSample: Int, samples: Int, final: Boolean): EndpointResult {
        if (terminal || nativeMode == false || startSample != total || samples <= 0 ||
            samples > nativeInputCapacity() || (samples != 512 && !final)) return invalidate()
        nativeMode = true
        return consume(probability, samples, final)
    }

    fun invalidate(): EndpointResult {
        terminal = true
        high = 0; quiet = 0; speech = false
        return EndpointResult.INVALID
    }

    private fun consume(probability: Float, samples: Int, final: Boolean): EndpointResult {
        if (!probability.isFinite() || probability !in 0f..1f || total > 480000 - samples) return invalidate()
        total += samples
        when {
            probability >= .8f -> { high += samples; quiet = 0; if (high >= 2560) speech = true }
            probability <= .2f -> { high = 0; if (speech) quiet += samples }
            else -> { high = 0; quiet = 0 }
        }
        val result = when {
            speech && quiet >= 8000 -> EndpointResult.COMPLETE
            !speech && total >= 80000 -> EndpointResult.NO_SPEECH
            total >= 480000 -> EndpointResult.LIMIT
            final -> EndpointResult.INCOMPLETE
            else -> EndpointResult.CONTINUE
        }
        terminal = result != EndpointResult.CONTINUE
        return result
    }

    fun confirmedSpeech() = speech
    fun elapsedSamples() = total
}

internal data class NativeVadObservation(val probability: Float, val startSample: Int,
                                         val samples: Int, val final: Boolean)

/** Native-worker receiver. Include generation cancellation and model-lease validity in verified;
 * the controller must recheck its token before committing a returned decision. No echo/confidence grant. */
internal class NativeVadEndpointBridge(private val verified: () -> Boolean = { false }) {
    private val endpoint = EndpointDetector()
    private var closed = false
    private fun validLease() = try { verified() } catch (_: Exception) { false }
    fun inputCapacity(): Int {
        if (closed || !validLease()) { close(); return 0 }
        return endpoint.nativeInputCapacity()
    }
    fun elapsedSamples() = endpoint.elapsedSamples()

    fun consume(frame: NativeVadObservation): EndpointResult {
        if (closed || !validLease()) { close(); return EndpointResult.INVALID }
        val result = endpoint.advanceNative(frame.probability, frame.startSample, frame.samples, frame.final)
        if (!validLease()) { close(); return EndpointResult.INVALID }
        if (result != EndpointResult.CONTINUE) closed = true
        return result
    }

    fun close() { closed = true; endpoint.invalidate() }
}
