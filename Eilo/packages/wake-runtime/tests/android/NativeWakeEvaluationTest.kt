package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject
import java.io.File

/** Explicit host-JVM evaluation only. Not part of the app's normal test source set. */
class NativeWakeEvaluationTest {
    @Test fun realJNIAndKotlinDecoderAcceptFrozenSyntheticSet() {
        val root=File(System.getProperty("eilo.wake.root"))
        val provenance=JSONObject(File(root,"provenance.json").readText())
        val cache=File(System.getProperty("eilo.wake.cache"))
        val host=File(cache,provenance.getJSONObject("runtime").getString("directory"))
        val runtime=NativeWakeRuntime(loadLibrary={ name ->
            val library=when(name) {
                "onnxruntime" -> File(host,"lib/libonnxruntime.dylib")
                "sherpa-onnx-c-api" -> File(host,"lib/libsherpa-onnx-c-api.dylib")
                "eilo_wake_jni" -> File(System.getProperty("eilo.wake.library"))
                else -> error("unexpected library")
            }
            System.load(library.absolutePath)
        })
        assertSame(NativeWakeJNI,runtime.load());assertSame(NativeWakeJNI,runtime.load())
        assertTrue(NativeWakeJNI.runtimeCompatible())

        WakeRuntimeEvaluation.run(root,cache,NativeWakeJNI,{testController()},
            "sherpa-onnx 1.13.8 host macOS ARM64",
            "Host JVM JNI + actual Kotlin binding/controller; not Android device execution",
            "PASS: explicit pinned host loading; no Android execution",
            File(cache,"android/host-jni-results.json"))
    }
}
