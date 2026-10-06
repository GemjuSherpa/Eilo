package com.eilo.foundation

enum class ControllerState(val wireValue: String) {
    SETUP("setup"), PERMISSION_REQUIRED("permission_required"), STOPPED("stopped"),
    STANDBY("standby"), CAPTURING("listening"), THINKING("thinking"), SPEAKING("speaking"),
    PAUSED("paused"), ERROR("error")
}
enum class ControllerEvent { SETUP_REQUIRED, READY, START, SPEECH_DETECTED, ENDPOINT, SPEECH_READY, PLAYBACK_FINISHED, PAUSE, RESUME, STOP, FAILURE }

/** Effects must be synchronous, nonblocking and idempotent; async completions return through the controller. */
interface ControllerEffects {
    fun cancelWork()
    fun releaseCapture()
    fun clearVolatileContext()
}
class NoopControllerEffects : ControllerEffects {
    override fun cancelWork() {}
    override fun releaseCapture() {}
    override fun clearVolatileContext() {}
}

/** Sole native state authority. Every mutation/observation is serialized on this monitor. */
class NativeController(private val diagnostics: SafeDiagnostics = SafeDiagnostics(), private val effects: ControllerEffects = NoopControllerEffects()) {
    private var currentState = ControllerState.STOPPED
    private var currentError: SafeError? = null
    @Synchronized fun state(): ControllerState = currentState
    @Synchronized fun error(): SafeError? = currentError
    @Synchronized fun dispatch(event: ControllerEvent, failure: SafeError = SafeError.UNEXPECTED): Boolean {
        if (event == ControllerEvent.STOP) return stop()
        val next = nextState(currentState, event) ?: return false
        currentState = next
        currentError = if (next == ControllerState.ERROR) failure else null
        if (next == ControllerState.ERROR) diagnostics.record(SafeComponent.CONTROLLER, failure, SafeSeverity.ERROR)
        return true
    }
    @Synchronized fun stop(): Boolean {
        currentState = ControllerState.STOPPED
        currentError = null
        var failed = false
        for (cleanup in listOf(effects::cancelWork, effects::releaseCapture, effects::clearVolatileContext)) {
            try { cleanup() } catch (_: Exception) { failed = true }
        }
        diagnostics.clear()
        if (failed) {
            currentState = ControllerState.ERROR; currentError = SafeError.UNEXPECTED
            diagnostics.record(SafeComponent.CONTROLLER, SafeError.UNEXPECTED, SafeSeverity.ERROR)
        }
        return !failed
    }
    companion object {
        fun nextState(state: ControllerState, event: ControllerEvent): ControllerState? = when (event) {
            ControllerEvent.STOP -> ControllerState.STOPPED
            ControllerEvent.FAILURE -> ControllerState.ERROR
            ControllerEvent.SETUP_REQUIRED -> if (state == ControllerState.STOPPED) ControllerState.SETUP else null
            ControllerEvent.READY -> if (state in setOf(ControllerState.SETUP, ControllerState.ERROR)) ControllerState.STOPPED else null
            ControllerEvent.START -> if (state == ControllerState.STOPPED) ControllerState.STANDBY else null
            ControllerEvent.SPEECH_DETECTED -> if (state == ControllerState.STANDBY) ControllerState.CAPTURING else null
            ControllerEvent.ENDPOINT -> if (state == ControllerState.CAPTURING) ControllerState.THINKING else null
            ControllerEvent.SPEECH_READY -> if (state == ControllerState.THINKING) ControllerState.SPEAKING else null
            ControllerEvent.PLAYBACK_FINISHED -> if (state == ControllerState.SPEAKING) ControllerState.STANDBY else null
            ControllerEvent.PAUSE -> if (state in setOf(ControllerState.STANDBY, ControllerState.CAPTURING, ControllerState.THINKING, ControllerState.SPEAKING)) ControllerState.PAUSED else null
            ControllerEvent.RESUME -> if (state == ControllerState.PAUSED) ControllerState.STANDBY else null
        }
    }
}
