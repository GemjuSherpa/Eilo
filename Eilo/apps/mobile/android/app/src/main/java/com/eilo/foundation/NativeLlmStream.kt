package com.eilo.foundation

internal interface NativeLlmApi {
    fun create(): Long
    fun load(handle: Long, descriptor: Int, threads: Int): Int
    fun countTokens(handle: Long, text: ByteArray, count: Int): Int = -3
    fun begin(handle: Long, prompt: ByteArray, count: Int, outputLimit: Int): Int
    fun next(handle: Long, output: ByteArray, count: IntArray): Int
    fun cancel(handle: Long)
    fun destroy(handle: Long)
}

internal object UnavailableLlmApi : NativeLlmApi {
    override fun create() = 0L
    override fun load(handle: Long, descriptor: Int, threads: Int) = -3
    override fun begin(handle: Long, prompt: ByteArray, count: Int, outputLimit: Int) = -3
    override fun next(handle: Long, output: ByteArray, count: IntArray): Int {
        output.fill(0); count.fill(0); return -3
    }
    override fun cancel(handle: Long) {}
    override fun destroy(handle: Long) {}
}

internal enum class LlmFailureReason { UNAVAILABLE, CANCELLED }
internal class LlmFailure(val reason: LlmFailureReason) : IllegalStateException("LLM unavailable")

/** One serialized native worker handles load/generation/close. Only requestCancellation
 * may run concurrently. Join that worker before dropping the stream's last reference.
 * Descriptor/prompt/raw tokens never enter JS. The immutable FD must already be hashed
 * and exclusively borrowed until load returns. The lease also binds controller/privacy.
 */
internal class NativeLlmStream(
    private val allowed: () -> Boolean,
    private val api: NativeLlmApi = UnavailableLlmApi,
) : AutoCloseable {
    private enum class Phase { CREATED, LOADED, GENERATING, CLOSED }
    private val lifetime = Any()
    private var handle = 0L
    private var cancelled = false
    private var phase = Phase.CREATED
    private val scratch = ByteArray(1024)
    private val count = IntArray(1)

    init {
        if (!validLease()) throw LlmFailure(LlmFailureReason.UNAVAILABLE)
        val candidate = try { api.create() } catch (_: LinkageError) { 0L } catch (_: Exception) { 0L }
        if (candidate <= 0) throw LlmFailure(LlmFailureReason.UNAVAILABLE)
        handle = candidate
        if (!validLease()) fail()
    }

    fun load(verifiedDescriptor: Int, threads: Int = 2) {
        val current = checkedHandle()
        if (phase != Phase.CREATED || verifiedDescriptor < 0 || threads !in 1..8) fail()
        accept(native { api.load(current, verifiedDescriptor, threads) })
        phase = Phase.LOADED
    }

    /** Actual loaded vocabulary; worker-only, same special-token flags as begin. */
    fun countTokens(text: String): Int {
        val bytes = text.toByteArray(Charsets.UTF_8)
        try {
            val current = checkedHandle()
            if (phase != Phase.LOADED || bytes.size !in 1..16384 || bytes.any { it == 0.toByte() }) fail()
            val result = native { api.countTokens(current, bytes, bytes.size) }; checkedHandle()
            if (result !in 1..32768) fail(result)
            return result
        } finally { bytes.fill(0) }
    }

    /** Borrows preformatted bytes for this call; it retains no prompt/String. */
    fun begin(prompt: ByteArray, outputLimit: Int) {
        val current = checkedHandle()
        if (phase != Phase.LOADED || prompt.size !in 1..16384 || prompt.any { it == 0.toByte() } ||
            outputLimit !in 1..256) fail()
        accept(native { api.begin(current, prompt, prompt.size, outputLimit) })
        phase = Phase.GENERATING
    }

    /** Raw bytes can split UTF-8. The shared scratch is borrowed only in consume and
     * then cleared. Revalidate the downstream transaction before speech/display/storage;
     * this callback cannot undo cancellation after it returns and grants no speech rights.
     */
    fun withNextPiece(consume: (ByteArray, Int) -> Unit): Boolean {
        try {
            val current = checkedHandle()
            if (phase != Phase.GENERATING) fail()
            val result = native { api.next(current, scratch, count) }
            checkedHandle()
            if (result == 0 && count[0] == 0) { close(); return false }
            if (result != 1 || count[0] !in 1..1024) fail(result)
            consume(scratch, count[0])
            return true
        } finally { scratch.fill(0); count.fill(0) }
    }

    /** The short lifetime gate protects cancel from detached handles. It never waits
     * for native decode or destroys the live worker's handle. False means native signal
     * failed; local cancellation still permanently rejects subsequent output.
     */
    fun requestCancellation(): Boolean = synchronized(lifetime) {
        cancelled = true
        try { if (handle > 0) api.cancel(handle); true }
        catch (_: LinkageError) { false } catch (_: Exception) { false }
    }

    override fun close() {
        val old = synchronized(lifetime) { cancelled = true; val old = handle; handle = 0L; old }
        phase = Phase.CLOSED; scratch.fill(0); count.fill(0)
        if (old > 0) {
            var failed = false
            try { api.cancel(old) } catch (_: LinkageError) { failed = true } catch (_: Exception) { failed = true }
            try { api.destroy(old) } catch (_: LinkageError) { failed = true } catch (_: Exception) { failed = true }
            if (failed) throw LlmFailure(LlmFailureReason.UNAVAILABLE)
        }
    }

    private fun validLease() = try { allowed() } catch (_: Exception) { false }
    private fun checkedHandle(): Long {
        val state = synchronized(lifetime) { handle to cancelled }
        if (state.first <= 0 || state.second || !validLease()) fail(if (state.second) -2 else -3)
        return state.first
    }
    private fun accept(result: Int) { checkedHandle(); if (result != 0) fail(result) }
    private inline fun <T> native(operation: () -> T): T = try { operation() }
        catch (_: LinkageError) { fail() } catch (_: Exception) { fail() }
    private fun fail(result: Int = -3): Nothing {
        close()
        throw LlmFailure(if (result == -2) LlmFailureReason.CANCELLED else LlmFailureReason.UNAVAILABLE)
    }
}
