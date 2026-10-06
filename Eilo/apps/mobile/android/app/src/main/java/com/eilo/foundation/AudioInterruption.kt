package com.eilo.foundation

enum class AudioInterruption { CALL, FOCUS_LOSS, PERMISSION_LOSS, CAPTURE_CONTENTION, ENGINE_RESET }
/** Interruptions never grant consent or resume. Every event invalidates all volatile work. */
class AudioInterruptionHandler(private val controller: NativeController) {
    fun receive(event: AudioInterruption): Boolean = when(event) {
        AudioInterruption.CALL, AudioInterruption.FOCUS_LOSS, AudioInterruption.PERMISSION_LOSS,
        AudioInterruption.CAPTURE_CONTENTION, AudioInterruption.ENGINE_RESET -> controller.stop()
    }
}
