package com.eilo.foundation

internal interface VadStream {
    fun process(pcm: FloatArray, count: Int, final: Boolean): NativeVadObservation
    fun close()
}
internal interface NativeVadApi {
    fun create(model: String): Long
    fun process(handle: Long, pcm: FloatArray, count: Int, final: Boolean): NativeVadObservation?
    fun destroy(handle: Long)
}
internal object UnavailableVadApi : NativeVadApi {
    override fun create(model: String) = 0L
    override fun process(handle: Long, pcm: FloatArray, count: Int, final: Boolean): NativeVadObservation? = null
    override fun destroy(handle: Long) {}
}

/** Explicit native evaluation loading only; caller verifies immutable runtime/wrapper files.
 * The normal app never calls this loader, and model/runtime paths never come from JS. */
internal object NativeVadJni {
    private external fun createNative(path: ByteArray): Long
    private external fun processNative(handle: Long, pcm: FloatArray, count: Int, final: Boolean): DoubleArray?
    private external fun destroyNative(handle: Long)
    fun loadVerified(libraries: List<String>, verified: () -> Boolean): NativeVadApi {
        require(verified() && libraries.size == 2)
        val roles = listOf("libonnxruntime", "libeilo_vad_jni")
        libraries.forEachIndexed { i, path ->
            require(path.startsWith('/') && path.toByteArray(Charsets.UTF_8).size <= 4096 && !path.contains('\u0000'))
            require(path.substringAfterLast('/') in listOf(roles[i]+".so", roles[i]+".dylib"))
        }
        libraries.forEach { System.load(it) }
        require(verified())
        return object : NativeVadApi {
            override fun create(model: String): Long {
                val bytes = model.toByteArray(Charsets.UTF_8)
                return try { createNative(bytes) } finally { bytes.fill(0) }
            }
            override fun process(handle: Long, pcm: FloatArray, count: Int, final: Boolean): NativeVadObservation? {
                val values = processNative(handle, pcm, count, final) ?: return null
                if (values.size != 4 || values.any { !it.isFinite() } || values[0] !in 0.0..1.0 ||
                    values[1] !in 0.0..480000.0 || values[2] !in 1.0..512.0 ||
                    values[1].toInt().toDouble() != values[1] || values[2].toInt().toDouble() != values[2] ||
                    values[3] !in listOf(0.0, 1.0)) return null
                return NativeVadObservation(values[0].toFloat(), values[1].toInt(), values[2].toInt(), values[3] == 1.0)
            }
            override fun destroy(handle: Long) { destroyNative(handle) }
        }
    }
}

/** Worker-confined handle owner. Stop revokes the supplied generation/model predicate;
 * no capture/controller lock is held while calling or destroying native state. */
internal class NativeVadStream(model: String, private val verified: () -> Boolean,
                               private val api: NativeVadApi = UnavailableVadApi) : VadStream {
    private var handle = 0L
    private var nextSample = 0
    private fun validLease() = try { verified() } catch (_: Exception) { false }
    init {
        require(model.startsWith('/') && model.toByteArray(Charsets.UTF_8).size <= 4096 && !model.contains('\u0000') && validLease())
        val candidate = api.create(model)
        check(candidate > 0)
        if (!validLease()) { api.destroy(candidate); error("VAD unavailable") }
        handle = candidate
    }
    override fun process(pcm: FloatArray, count: Int, final: Boolean): NativeVadObservation {
        try {
            check(handle > 0 && validLease() && count in 1..512 && count <= pcm.size && (count == 512 || final) &&
                nextSample <= 480000-count && (0 until count).all { pcm[it].isFinite() && pcm[it] in -1f..1f })
            val frame = api.process(handle, pcm, count, final)
            check(frame != null && validLease() && frame.probability.isFinite() && frame.probability in 0f..1f &&
                frame.startSample == nextSample && frame.samples == count && frame.final == final)
            nextSample += count
            if (final) { close(); check(validLease()) }
            return frame
        } catch (_: Exception) { close(); error("VAD unavailable") }
    }
    override fun close() {
        val previous = handle; handle = 0
        if (previous > 0) api.destroy(previous)
    }
}
