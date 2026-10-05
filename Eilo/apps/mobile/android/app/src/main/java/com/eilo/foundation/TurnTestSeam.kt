package com.eilo.foundation

// Native-only injection seam. Not connected to UI or a production controller.
fun interface CaptureAdapter { fun capture(): FloatArray }
fun interface AsrAdapter { fun transcribe(samples: FloatArray): String }
fun interface ModelAdapter { fun reply(input: String, context: String): String }
fun interface TtsAdapter { fun speak(reply: String) }
fun interface MemoryAdapter { fun eligibleContext(): String }
enum class TurnTestResult { COMPLETED, ADAPTER_FAILED }

class TurnTestSeam(
    private val capture: CaptureAdapter,
    private val asr: AsrAdapter,
    private val model: ModelAdapter,
    private val tts: TtsAdapter,
    private val memory: MemoryAdapter,
) {
    fun runSyntheticTurn(): TurnTestResult {
        return try {
            val samples = capture.capture()
            val input = try { asr.transcribe(samples) } finally { samples.fill(0f) }
            val reply = model.reply(input, memory.eligibleContext())
            tts.speak(reply)
            TurnTestResult.COMPLETED
        } catch (_: Exception) {
            // No content or exception message escapes this native test seam.
            TurnTestResult.ADAPTER_FAILED
        }
    }
}
