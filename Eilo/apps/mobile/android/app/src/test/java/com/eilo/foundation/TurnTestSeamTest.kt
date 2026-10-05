package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test

class TurnTestSeamTest {
    @Test fun syntheticTurnUsesOnlyInjectedAdaptersAndClearsSamples() {
        val calls = mutableListOf<String>()
        val samples = floatArrayOf(0.25f)
        val seam = TurnTestSeam(
            CaptureAdapter { calls.add("capture"); samples },
            AsrAdapter { assertEquals(0.25f, it[0]); calls.add("asr"); "synthetic hello" },
            ModelAdapter { input, context ->
                assertEquals("synthetic hello", input); assertEquals("", context)
                calls.add("model"); "synthetic reply"
            },
            TtsAdapter { assertEquals("synthetic reply", it); calls.add("tts") },
            MemoryAdapter { calls.add("memory"); "" },
        )
        assertEquals(TurnTestResult.COMPLETED, seam.runSyntheticTurn())
        assertEquals(listOf("capture", "asr", "memory", "model", "tts"), calls)
        assertEquals(0f, samples[0])
    }
    @Test fun adapterFailureStopsDownstreamWorkAndReturnsOnlyCode() {
        val samples = floatArrayOf(0.5f)
        val seam = TurnTestSeam(
            CaptureAdapter { samples },
            AsrAdapter { throw IllegalStateException("synthetic private diagnostic") },
            ModelAdapter { _, _ -> fail("model must not run"); "" },
            TtsAdapter { fail("speech must not run") },
            MemoryAdapter { fail("memory must not run"); "" },
        )
        assertEquals(TurnTestResult.ADAPTER_FAILED, seam.runSyntheticTurn())
        assertEquals(0f, samples[0])
    }
}
