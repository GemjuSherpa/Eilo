package com.eilo.foundation

/** Explicit inference-worker loading of fixed app-packaged names; never arbitrary paths or JS.
 * Loading does not grant model readiness or capture permission. No default app caller is installed.
 * Failed/partially loaded instances never retry; native libraries cannot safely be unloaded here.
 * System linker/app packaging is the code-trust boundary, not the version probe alone.
 */
internal class NativeWakeRuntime(
    private val loadLibrary: (String)->Unit=System::loadLibrary,
    private val compatible: ()->Boolean=NativeWakeJNI::runtimeCompatible,
    private val api: NativeWakeAPI=NativeWakeJNI,
) {
    private var attempted=false
    private var ready=false
    @Synchronized fun load(): NativeWakeAPI? {
        if (!attempted) {
            attempted=true
            ready=try {
                for(name in listOf("onnxruntime","sherpa-onnx-c-api","eilo_wake_jni"))loadLibrary(name)
                compatible()
            } catch (_:LinkageError) { false } catch (_:Exception) { false }
        }
        return if(ready)api else null
    }
}
