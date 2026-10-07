package com.eilo.foundation

/** Keyword-only engine port, never conversational ASR. Must consume borrowed PCM synchronously. */
internal interface WakeKeywordStream {
    fun accept(samples: FloatArray, count: Int, sampleRate: Int)
    fun ready(): Boolean
    fun decode()
    fun keyword(): String
    fun reset()
    /** Release native feature/state buffers as well as the stream. */
    fun close()
}

internal data class WakeConfiguration(val phrase: String, val threshold: Float, val boost: Float) {
    init {
        require(phrase.matches(Regex("[A-Z]+(?: [A-Z]+){0,7}")) && phrase.length <= 64)
        require(threshold.isFinite() && threshold > 0f && threshold <= 1f)
        require(boost.isFinite() && boost > 0f && boost <= 10f)
    }
}

/** Metadata-only handoff; NativeController rechecks the original session/privacy/generation. */
internal class WakeLease { @Volatile var active=true }
internal class WakeActivation(private val token: GenerationToken, private val lease:WakeLease) {
    fun apply(controller: NativeController) = controller.wakeDetected(token) { lease.active }
}

/** Call only on a serialized native inference worker, never an audio callback/UI thread.
 * No backend is installed by default. Configuration and verified assets are independently required.
 * The synchronous backend borrows a bounded scratch frame; the adapter erases it before returning.
 */
internal class WakeDetector(
    private val configuration: WakeConfiguration,
    private val diagnostics: SafeDiagnostics = SafeDiagnostics(),
    private val verified: () -> Boolean = { false },
    private val open: (WakeConfiguration) -> WakeKeywordStream = { throw IllegalStateException() },
) {
    private val scratch=FloatArray(19200) // At most 100 ms at the maximum accepted 192 kHz rate.
    private var sampleRate:Int?=null
    private var releaseFailed=false
    private var stream: WakeKeywordStream?=null
    private var token: GenerationToken?=null
    private var lease:WakeLease?=null
    @Synchronized fun begin(expected: GenerationToken): Boolean {
        close()
        if(expected.cancelled || releaseFailed) return false
        return try {
            if(!verified()) return false
            val candidate=open(configuration);stream=candidate
            if(expected.cancelled || !verified()) { close();false } else { token=expected;lease=WakeLease();true }
        } catch (_: Exception) { close();false }
    }
    @Synchronized fun processPCM16(expected: GenerationToken, input: ShortArray, count: Int, sampleRate: Int): WakeActivation? {
        if(expected !== token || expected.cancelled) { if(expected === token) close();return null }
        if(sampleRate !in 8000..192000 || count !in 1..input.size || count > sampleRate/10) { close();return null }
        if(this.sampleRate != null && this.sampleRate != sampleRate) { close();return null }
        this.sampleRate=sampleRate
        val engine=stream ?: return null
        val currentLease=lease ?: return null
        return try {
            if(!verified()) { close();return null }
            for(i in 0 until count) scratch[i]=input[i]/32768f
            engine.accept(scratch,count,sampleRate)
            var steps=0
            var matched=false
            fun consumeResult() {
                val keyword=engine.keyword()
                matched=matched || keyword==configuration.phrase
                if(keyword.isNotEmpty()) engine.reset()
            }
            while(engine.ready()) {
                if(++steps > 32) { close();return null }
                engine.decode()
                consumeResult()
            }
            if(steps==0) consumeResult()
            if(expected.cancelled || !verified()) { close();return null }
            if(matched && expected === token && currentLease === lease) WakeActivation(expected,currentLease) else null
        } catch (_: Exception) { diagnostics.record(SafeComponent.MODEL,SafeError.UNAVAILABLE,SafeSeverity.ERROR);close();null }
        finally { scratch.fill(0f) }
    }
    @Synchronized fun close() {
        lease?.active=false;lease=null
        val previous=stream;stream=null;token=null;sampleRate=null;scratch.fill(0f)
        try { previous?.close() } catch (_: Exception) { releaseFailed=true;diagnostics.record(SafeComponent.MODEL,SafeError.UNAVAILABLE,SafeSeverity.ERROR) }
    }
}
