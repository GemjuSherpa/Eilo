package com.eilo.foundation

/** Native-only text. Never emit it through the UI bridge or diagnostics. */
internal data class AsrText(val text: String, val final: Boolean)
internal interface AsrStream : AutoCloseable {
    /** Synchronous borrowed PCM; implementations must not retain this scratch array. */
    fun accept(pcm: FloatArray, count: Int)
    fun text(finish: Boolean): String
}

/** One active turn, confined to the native inference worker. Stop cancels the token immediately;
 * cleanup is scheduled on this worker, never under a controller/capture lock.
 * A backend is opened lazily only after native activation and verification. */
internal class StreamingAsr(
    private val token: GenerationToken,
    private val allowed: () -> Boolean,
    private val open: () -> AsrStream
) : AutoCloseable {
    private val scratch = FloatArray(1600)
    private var stream: AsrStream? = null
    private var samples = 0
    private var closed = false
    private fun valid() = !closed && !token.cancelled && try { allowed() } catch (_: Exception) { false }

    fun accept(pcm: ShortArray, count: Int): Boolean {
        if (count !in 1..1600 || count > pcm.size || samples > 480000-count || !valid()) {
            close(); return false
        }
        return try {
            if (stream == null) stream = open()
            if (!valid()) { close(); return false }
            repeat(count) { scratch[it] = pcm[it]/32768f }
            stream!!.accept(scratch,count); samples += count
            if (!valid()) { close(); false } else true
        } catch (_: Exception) { close(); false }
        finally { scratch.fill(0f) }
    }

    fun poll(finish: Boolean = false): AsrText? {
        if (!valid() || stream == null) { close(); return null }
        return try {
            val text = stream!!.text(finish)
            if (!valid() || text.toByteArray(Charsets.UTF_8).size > 4096 || text.any { it=='\u0000' || (it.isISOControl() && it!='\n' && it!='\t') }) {
                close(); null
            } else {
                val result=AsrText(text.trim(),finish)
                if (finish) close()
                result
            }
        } catch (_: Exception) { close(); null }
    }
    override fun close() {
        if (closed) return
        closed=true; val previous=stream; stream=null
        scratch.fill(0f)
        try { previous?.close() } catch (_: Exception) { /* no content-bearing diagnostics */ }
    }
}
