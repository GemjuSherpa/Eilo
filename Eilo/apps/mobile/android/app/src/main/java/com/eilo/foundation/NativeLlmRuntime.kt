package com.eilo.foundation

import com.eilo.BuildConfig

internal object NativeLlmJni : NativeLlmApi {
    external fun runtimeCompatible(): Boolean
    override external fun create(): Long
    override external fun load(handle: Long, descriptor: Int, threads: Int): Int
    override external fun begin(handle: Long, prompt: ByteArray, count: Int, outputLimit: Int): Int
    override external fun next(handle: Long, output: ByteArray, count: IntArray): Int
    override external fun cancel(handle: Long)
    override external fun destroy(handle: Long)
}

/** Explicit Debug evaluation only, using a fixed app-packaged library name. Loading
 * never grants model readiness, permission or signed pack trust. There is no default
 * app caller. The system linker/package provenance remains the code-trust boundary.
 * Failed or partially loaded instances never retry; shared libraries cannot be unloaded.
 */
internal class NativeLlmRuntime(
    private val evaluationEnabled: Boolean = false,
    private val debugBuild: Boolean = BuildConfig.DEBUG,
    private val loadLibrary: (String) -> Unit = System::loadLibrary,
    private val compatible: () -> Boolean = NativeLlmJni::runtimeCompatible,
    private val api: NativeLlmApi = NativeLlmJni,
) {
    private var attempted = false
    private var ready = false
    @Synchronized fun load(): NativeLlmApi? {
        if (!attempted) {
            attempted = true
            ready = evaluationEnabled && debugBuild && try {
                loadLibrary("eilo_llm_jni"); compatible()
            } catch (_: LinkageError) { false } catch (_: Exception) { false }
        }
        return if (ready) api else null
    }
}
