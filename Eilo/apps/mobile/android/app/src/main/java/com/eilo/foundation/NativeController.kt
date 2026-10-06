package com.eilo.foundation

import java.util.UUID

enum class ControllerState(val wireValue: String) {
    SETUP("setup"), PERMISSION_REQUIRED("permission_required"), STOPPED("stopped"),
    STANDBY("standby"), CAPTURING("listening"), THINKING("thinking"), SPEAKING("speaking"),
    PAUSED("paused"), ERROR("error")
}
enum class ControllerEvent { SETUP_REQUIRED, READY, START, SPEECH_DETECTED, ENDPOINT, SPEECH_READY, PLAYBACK_FINISHED, PAUSE, RESUME, STOP, FAILURE }

/** Effects must be synchronous, nonblocking and idempotent; async completions return through the controller. */
interface ControllerEffects {
    fun playClause(clause: String)
    fun cancelWork()
    fun releaseCapture()
    fun clearVolatileContext()
}
class NoopControllerEffects : ControllerEffects {
    override fun playClause(clause: String) {}
    override fun cancelWork() {}
    override fun releaseCapture() {}
    override fun clearVolatileContext() {}
}

class GenerationToken internal constructor(val sessionId: UUID, val operationId: UUID, val generation: Long, val privacyEpoch: Long) {
    @Volatile var cancelled: Boolean = false
        internal set
}

enum class PrivacyChange { LOCK, UNLOCK, PRIVATE_SESSION, HISTORY_SESSION, IDENTITY_RESET, DELETE_ALL }
enum class PrivateEffect { READ_MEMORY, COMMIT_HISTORY, DISPLAY_PRIVATE }
fun interface PrivateEffectGate { fun allows(effect: PrivateEffect): Boolean }

/** Sole native state authority. Every mutation/observation is serialized on this monitor. */
class NativeController(private val diagnostics: SafeDiagnostics = SafeDiagnostics(), private val effects: ControllerEffects = NoopControllerEffects(), private val privateGate: PrivateEffectGate = PrivateEffectGate { false }, private val clock: NativeClock = MonotonicClock(), private val scheduler: IdleScheduler = NativeIdleScheduler()) {
    private var idleTask: IdleCancellation? = null
    private var idleStarted: Long? = null
    private var hasConversation = false
    private fun clearIdle() { idleTask?.cancel(); idleTask=null; idleStarted=null }
    private fun updateIdle() {
        clearIdle()
        if (currentState == ControllerState.STANDBY && hasConversation) {
            idleStarted=clock.milliseconds()
            val expected=activeToken ?: return
            idleTask=scheduler.schedule(60_000) { expireIdle(expected) }
        }
    }
    @Synchronized private fun expireIdle(expected: GenerationToken) {
        if (!accepts(expected) || currentState != ControllerState.STANDBY) return
        val started=idleStarted ?: return
        val elapsed=clock.milliseconds()-started
        if (elapsed < 60_000) { idleTask=scheduler.schedule(60_000-elapsed.coerceAtLeast(0)) { expireIdle(expected) }; return }
        endSessionPreservingCapture()
    }
    private fun endSessionPreservingCapture(): Boolean {
        clearIdle(); invalidateGeneration(); hasConversation=false
        val expectedGeneration=generation; val expectedEpoch=privacyEpoch
        return try {
            effects.cancelWork(); effects.clearVolatileContext()
            if (generation != expectedGeneration || privacyEpoch != expectedEpoch) return false
            sessionId=UUID.randomUUID(); currentState=ControllerState.STANDBY; issueGeneration(); true
        } catch (_: Exception) { stop(); currentState=ControllerState.ERROR; currentError=SafeError.UNEXPECTED; diagnostics.record(SafeComponent.CONTROLLER,SafeError.UNEXPECTED,SafeSeverity.ERROR); false }
    }
    private var sessionId = UUID.randomUUID()
    private var privacyEpoch = 0L
    private var locked = false
    private var privateSession = true
    private var generation = 0L
    private var activeToken: GenerationToken? = null
    @Synchronized fun token(): GenerationToken? = activeToken
    private fun invalidateGeneration() {
        activeToken?.cancelled = true; activeToken = null
        if (generation == 9007199254740991L) { sessionId = UUID.randomUUID(); generation = 0 } else generation++
    }
    private fun issueGeneration() {
        invalidateGeneration()
        activeToken = GenerationToken(sessionId, UUID.randomUUID(), generation, privacyEpoch)
    }
    private fun accepts(token: GenerationToken?): Boolean = token != null && token === activeToken && !token.cancelled && token.privacyEpoch == privacyEpoch
    private var currentState = ControllerState.STOPPED
    private var currentError: SafeError? = null
    @Synchronized fun state(): ControllerState = currentState
    @Synchronized fun error(): SafeError? = currentError
    @Synchronized fun dispatch(event: ControllerEvent, failure: SafeError = SafeError.UNEXPECTED, token: GenerationToken? = null): Boolean {
        if (locked && event in setOf(ControllerEvent.START,ControllerEvent.RESUME)) return false
        if (event == ControllerEvent.STOP) return stop()
        if (event in setOf(ControllerEvent.SPEECH_DETECTED, ControllerEvent.ENDPOINT, ControllerEvent.SPEECH_READY, ControllerEvent.PLAYBACK_FINISHED, ControllerEvent.FAILURE) && !accepts(token)) return false
        val next = nextState(currentState, event) ?: return false
        if (event == ControllerEvent.START || event == ControllerEvent.SPEECH_DETECTED || event == ControllerEvent.PLAYBACK_FINISHED || event == ControllerEvent.RESUME) issueGeneration()
        if ((event == ControllerEvent.PAUSE || event == ControllerEvent.FAILURE) && !stop()) return false
        currentState = next
        if (event == ControllerEvent.SPEECH_DETECTED) hasConversation=true
        try { updateIdle() } catch (_: Exception) { stop(); currentState=ControllerState.ERROR; currentError=SafeError.UNEXPECTED; return false }
        currentError = if (next == ControllerState.ERROR) failure else null
        if (next == ControllerState.ERROR) diagnostics.record(SafeComponent.CONTROLLER, failure, SafeSeverity.ERROR)
        return true
    }
    @Synchronized fun endConversation(): Boolean {
        if (currentState !in setOf(ControllerState.STANDBY,ControllerState.CAPTURING,ControllerState.THINKING,ControllerState.SPEAKING)) return false
        return endSessionPreservingCapture()
    }
    @Synchronized fun privacyTransition(change: PrivacyChange): Boolean {
        if (privacyEpoch == 9007199254740991L) { sessionId=UUID.randomUUID(); privacyEpoch=0 } else privacyEpoch++
        when (change) {
            PrivacyChange.LOCK -> locked=true
            PrivacyChange.UNLOCK -> locked=false
            PrivacyChange.PRIVATE_SESSION, PrivacyChange.IDENTITY_RESET, PrivacyChange.DELETE_ALL -> privateSession=true
            PrivacyChange.HISTORY_SESSION -> privateSession=false
        }
        return stop()
    }
    /** Native-only capability seam. Protected store/auth integration remains separately gated. */
    @Synchronized fun guardedPrivateEffect(token: GenerationToken, effect: PrivateEffect, action: () -> Unit): Boolean {
        if (!accepts(token) || locked || privateSession || currentState in setOf(ControllerState.STOPPED,ControllerState.SETUP,ControllerState.ERROR)) return false
        return try { if (!privateGate.allows(effect) || !accepts(token)) return false; action(); accepts(token) } catch (_: Exception) { stop(); currentState=ControllerState.ERROR; currentError=SafeError.UNEXPECTED; diagnostics.record(SafeComponent.MEMORY,SafeError.UNEXPECTED,SafeSeverity.ERROR); false }
    }
    @Synchronized fun releaseSpeech(token: GenerationToken, clause: String): Boolean {
        if (!accepts(token) || currentState !in setOf(ControllerState.THINKING, ControllerState.SPEAKING)) return false
        clearIdle()
        return try {
            effects.playClause(clause)
            if (!accepts(token)) return false
            currentState = ControllerState.SPEAKING; true
        } catch (_: Exception) { stop(); currentState = ControllerState.ERROR; currentError = SafeError.UNEXPECTED; diagnostics.record(SafeComponent.SPEECH, SafeError.UNEXPECTED, SafeSeverity.ERROR); false }
    }
    @Synchronized fun cancelGeneration() {
        invalidateGeneration()
        try { effects.cancelWork() } catch (_: Exception) { stop(); currentState = ControllerState.ERROR; currentError = SafeError.UNEXPECTED; return }
        if (currentState in setOf(ControllerState.CAPTURING,ControllerState.THINKING,ControllerState.SPEAKING)) { currentState = ControllerState.STANDBY; issueGeneration(); updateIdle() }
    }
    @Synchronized fun stop(): Boolean {
        clearIdle(); hasConversation=false
        invalidateGeneration()
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
