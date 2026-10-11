package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test

class NativeWakeRuntimeTest {
    @Test fun constructionDoesNotLoadAndSuccessLoadsFixedNamesOnceBeforeProbe() {
        val calls=mutableListOf<String>();var probes=0
        val runtime=NativeWakeRuntime({calls.add(it)},{probes++;assertEquals(listOf("onnxruntime","sherpa-onnx-c-api","eilo_wake_jni"),calls);true},NativeWakeAPI.unavailable)
        assertTrue(calls.isEmpty());assertEquals(0,probes)
        assertSame(NativeWakeAPI.unavailable,runtime.load());assertSame(NativeWakeAPI.unavailable,runtime.load())
        assertEquals(3,calls.size);assertEquals(1,probes)
    }
    @Test fun partialLinkFailureNeverProbesOrRetries() {
        for(failure in listOf<Throwable>(UnsatisfiedLinkError(),SecurityException(),IllegalStateException())) {
            val calls=mutableListOf<String>();var probes=0
            val runtime=NativeWakeRuntime({ calls.add(it);if(it=="sherpa-onnx-c-api")throw failure },{probes++;true})
            assertNull(runtime.load());assertNull(runtime.load())
            assertEquals(listOf("onnxruntime","sherpa-onnx-c-api"),calls);assertEquals(0,probes)
        }
    }
    @Test fun incompatibleMissingOrThrowingProbeNeverReturnsAPI() {
        for(probe in listOf<()->Boolean>({false},{throw UnsatisfiedLinkError()},{error("synthetic")})) {
            var loads=0;val runtime=NativeWakeRuntime({loads++},probe)
            assertNull(runtime.load());assertNull(runtime.load());assertEquals(3,loads)
        }
        // Normal host unit tests never load the evaluation JNI library.
        assertFalse(NativeWakeJNI.runtimeCompatible())
    }
}
