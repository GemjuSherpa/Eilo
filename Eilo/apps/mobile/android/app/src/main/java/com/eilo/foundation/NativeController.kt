package com.eilo.foundation

import java.util.UUID

enum class ControllerState(val wireValue: String) {
    SETUP("setup"), PERMISSION_REQUIRED("permission_required"), STOPPED("stopped"),
    STANDBY("standby"), CAPTURING("listening"), THINKING("thinking"), SPEAKING("speaking"),
    PAUSED("paused"), ERROR("error")
}
enum class ControllerEvent { SETUP_REQUIRED, READY, START, SPEECH_DETECTED, ENDPOINT, SPEECH_READY, PLAYBACK_FINISHED, PAUSE, RESUME, STOP, FAILURE }

/** Lifecycle effects are idempotent. Device opening uses beginCapture off the UI thread. */
interface ControllerEffects {
    fun setOutputGain(gain:Float) {}
    fun startCapture(): Boolean
    fun beginCapture(completion: (Boolean) -> Unit, failure: () -> Unit) { completion(startCapture()) }
    fun playClause(clause: String)
    fun cancelWork()
    fun releaseCapture()
    fun clearVolatileContext()
}
class NoopControllerEffects : ControllerEffects {
    override fun startCapture() = false
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
fun interface PrivateEffectGate { fun allows(effect: PrivateEffect): Boolean;fun invalidate() {} }

/** Sole native state authority. Every mutation/observation is serialized on this monitor. */
class NativeController(private val diagnostics: SafeDiagnostics = SafeDiagnostics(), private val effects: ControllerEffects = NoopControllerEffects(), private val privateGate: PrivateEffectGate = PrivateEffectGate { false }, private val clock: NativeClock = MonotonicClock(), private val scheduler: IdleScheduler = NativeIdleScheduler(), private var permission: MicrophonePermissionAdapter = UnavailablePermissionAdapter(), private val models: ModelReadinessAdapter = MissingModelReadiness()) {
    private val playback=PlaybackRejection(clock::milliseconds)
    private var interruptedCapture:GenerationToken?=null
    private var independentCapture:(()->Boolean)?=null
    @Synchronized internal fun recognitionAllowed(token:GenerationToken):Boolean {
        if(currentState!=ControllerState.CAPTURING || !accepts(token))return false
        if(playback.allowsAudio())return true
        val verify=independentCapture ?: return false
        return try {interruptedCapture===token && verify() && interruptedCapture===token && accepts(token)}catch(_:Exception){stop();false}
    }
    @Synchronized fun modelStatus(): ModelStatus = try { models.status() } catch (_: Exception) { ModelStatus.CORRUPT }
    @Synchronized fun modelsChanged() { if(modelStatus()!=ModelStatus.READY) { stop();if(currentState==ControllerState.STOPPED)currentState=ControllerState.SETUP } else if(currentState==ControllerState.SETUP) currentState=ControllerState.STOPPED }
    @Synchronized fun setOutputGain(gain:Float):Boolean {
      if(!gain.isFinite() || gain<0f || gain>1f) return false
      return try { effects.setOutputGain(gain);true } catch (_:Exception) { diagnostics.record(SafeComponent.SPEECH,SafeError.UNAVAILABLE,SafeSeverity.WARNING);false }
    }
    private var speakerRequired=false
    @Synchronized fun speakerConfirmationRequired() = speakerRequired
    @Synchronized fun routeDisconnected() { speakerRequired=true; stop() }
    @Synchronized fun confirmSpeaker(): Boolean { if (locked) return false; speakerRequired=false; return true }
    private var stopping=false
    private var startIntent: UUID? = null
    private var capturePending = false
    @Synchronized fun captureIsPending() = capturePending
    private var captureIntent: UUID? = null
    private var permissionPrompted=false
    private fun permissionGranted(): Boolean = try { permission.status() == MicrophonePermission.GRANTED } catch (_: Exception) { false }
    /** Binding/rebinding an activity never restores listening or prompts. */
    @Synchronized fun bindPermissionAdapter(adapter: MicrophonePermissionAdapter) { stop(); permission=adapter }
    @Synchronized fun snapshot(): Map<String, Any> {
        val result=mutableMapOf<String,Any>("modelStatus" to modelStatus().wireValue,"version" to 1,"state" to currentState.wireValue,"sessionId" to sessionId.toString(),"operationId" to (activeToken?.operationId ?: stoppedOperationId).toString(),"generation" to generation,"privacyEpoch" to privacyEpoch)
        if (currentState == ControllerState.ERROR) result["errorCode"]=(currentError ?: SafeError.UNEXPECTED).name.lowercase(java.util.Locale.ROOT)
        return result.toMap()
    }
    @Synchronized fun permissionChanged() { if (!permissionGranted() && (startIntent != null || activeToken != null)) stop() }
    @Synchronized private fun start(): Boolean {
        if (stopping || startIntent != null || locked || currentState !in setOf(ControllerState.STOPPED,ControllerState.PERMISSION_REQUIRED,ControllerState.PAUSED)) return false
        if(modelStatus()!=ModelStatus.READY) { modelsChanged();return false }
        val intent=UUID.randomUUID(); startIntent=intent
        return try {
            when (permission.status()) {
                MicrophonePermission.GRANTED -> completeStart(intent,MicrophonePermission.GRANTED)
                MicrophonePermission.NOT_REQUESTED -> {
                    if (permissionPrompted) { startIntent=null; currentState=ControllerState.PERMISSION_REQUIRED; false }
                    else { permissionPrompted=true; currentState=ControllerState.PERMISSION_REQUIRED; permission.request { completeStart(intent,it) }; true }
                }
                MicrophonePermission.DENIED -> { startIntent=null; currentState=ControllerState.PERMISSION_REQUIRED; currentError=null; false }
                MicrophonePermission.UNAVAILABLE -> { stop(); currentState=ControllerState.ERROR; currentError=SafeError.UNAVAILABLE; false }
            }
        } catch (_: Exception) { stop(); currentState=ControllerState.ERROR; currentError=SafeError.UNEXPECTED; diagnostics.record(SafeComponent.CAPTURE,SafeError.UNEXPECTED,SafeSeverity.ERROR); false }
    }
    @Synchronized private fun completeStart(intent: UUID, result: MicrophonePermission): Boolean {
        if (startIntent != intent || capturePending || locked) return false
        if (modelStatus()!=ModelStatus.READY) { modelsChanged(); return false }
        if (result != MicrophonePermission.GRANTED || !permissionGranted()) {
            startIntent=null; currentState=ControllerState.PERMISSION_REQUIRED; currentError=null; return false
        }
        capturePending=true
        // A pending open has no generation and cannot report standby/listening prematurely.
        val immediate = java.util.concurrent.atomic.AtomicReference<Boolean?>(null)
        return try {
            effects.beginCapture({ opened -> immediate.set(finishCapture(intent,opened)) }, { captureFailed(intent) })
            immediate.get() ?: true
        } catch (_: Exception) { captureFailed(intent); false }
    }
    @Synchronized private fun finishCapture(intent: UUID, opened: Boolean): Boolean {
        if (startIntent != intent || !capturePending) return false
        if (!opened || locked || currentState !in setOf(ControllerState.STOPPED,ControllerState.PERMISSION_REQUIRED,ControllerState.PAUSED) || !permissionGranted() || modelStatus()!=ModelStatus.READY) {
            stop()
            if (!opened) { currentState=ControllerState.ERROR; currentError=SafeError.UNAVAILABLE }
            return false
        }
        if (startIntent != intent || !capturePending) return false
        startIntent=null; capturePending=false; captureIntent=intent
        issueGeneration(); currentState=ControllerState.STANDBY; currentError=null; return true
    }
    @Synchronized private fun captureFailed(intent: UUID) {
        if (startIntent != intent && captureIntent != intent) return
        stop(); currentState=ControllerState.ERROR; currentError=SafeError.UNAVAILABLE
        diagnostics.record(SafeComponent.CAPTURE,SafeError.UNAVAILABLE,SafeSeverity.ERROR)
    }
    private var idleTask: IdleCancellation? = null
    private var idleStarted: Long? = null
    private var hasConversation = false
    private val genericDialogue=mutableListOf<QwenTurn>()
    private fun clearIdle() {
        val previous=idleTask; idleTask=null; idleStarted=null
        try { previous?.cancel() } catch (_: Exception) { diagnostics.record(SafeComponent.CONTROLLER,SafeError.UNEXPECTED,SafeSeverity.WARNING) }
    }
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
        if (!permissionGranted()) { stop(); return false }
        clearIdle(); invalidateGeneration(); hasConversation=false;genericDialogue.clear()
        val expectedGeneration=generation; val expectedEpoch=privacyEpoch
        return try {
            playback.cancel();effects.cancelWork(); effects.clearVolatileContext()
            if (generation != expectedGeneration || privacyEpoch != expectedEpoch) return false
            sessionId=UUID.randomUUID(); currentState=ControllerState.STANDBY; issueGeneration(); true
        } catch (_: Exception) { stop(); currentState=ControllerState.ERROR; currentError=SafeError.UNEXPECTED; diagnostics.record(SafeComponent.CONTROLLER,SafeError.UNEXPECTED,SafeSeverity.ERROR); false }
    }
    /** Volatile native context only; never a protected-history or persistence authority. */
    @Synchronized internal fun genericContext(token:GenerationToken):List<QwenTurn>? = if(accepts(token) && hasConversation && currentState in listOf(ControllerState.CAPTURING,ControllerState.THINKING,ControllerState.SPEAKING))genericDialogue.toList() else null
    @Synchronized internal fun recordGenericTurn(token:GenerationToken,user:String,reply:String){
        if(!accepts(token) || !hasConversation || currentState !in listOf(ControllerState.THINKING,ControllerState.SPEAKING) || user.isEmpty() || reply.isEmpty() || user.toByteArray().size>4096 || reply.toByteArray().size>4096)return
        genericDialogue+=listOf(QwenTurn(QwenRole.USER,user),QwenTurn(QwenRole.ASSISTANT,reply))
        while(genericDialogue.size>8 || genericDialogue.sumOf{it.text.toByteArray().size}>8192){genericDialogue.removeAt(0);genericDialogue.removeAt(0)}
    }
    @Synchronized internal fun beginGenericFollowup(expected:GenerationToken):GenerationToken? {
        if(currentState!=ControllerState.STANDBY || !hasConversation || !accepts(expected) || !playback.allowsAudio() || !dispatch(ControllerEvent.SPEECH_DETECTED,token=expected))return null
        return activeToken
    }
    private var sessionId = UUID.randomUUID()
    private var privacyEpoch = 0L
    private var locked = false
    private var privateSession = true
    private var stoppedOperationId=UUID.randomUUID()
    private var generation = 0L
    private var activeToken: GenerationToken? = null
    private var llmWork: LlmWorkTicket? = null
    /** Mint/attach before scheduling. One native model job per current thinking turn. */
    @Synchronized internal fun prepareLlmWork(token: GenerationToken, cancel: () -> Boolean): LlmWorkTicket? {
        if (stopping || currentState != ControllerState.THINKING || !accepts(token) || llmWork != null) return null
        return LlmWorkTicket(this, token, cancel).also { llmWork = it }
    }
    @Synchronized internal fun llmWorkAllowed(ticket: LlmWorkTicket): Boolean =
        ticket.controller === this && llmWork === ticket && !ticket.cancelled &&
            currentState in setOf(ControllerState.THINKING, ControllerState.SPEAKING) && !stopping && accepts(ticket.token)

    /** Borrowed raw output only. This transaction grants no speech/display/storage permission.
     * Consumer must perform only bounded native buffer work: no IO, inference or worker join.
     * Token and pack checks are serialized with Stop/privacy transitions. */
    @Synchronized internal fun consumeLlmPiece(ticket: LlmWorkTicket, verified: () -> Boolean,
        bytes: ByteArray, count: Int, consume: (ByteArray, Int) -> Unit): Boolean {
        if (!llmWorkAllowed(ticket)) return false
        return try {
            if (!verified() || !llmWorkAllowed(ticket)) return false
            consume(bytes, count)
            verified() && llmWorkAllowed(ticket)
        } catch (_: Exception) { stop(); false }
    }
    /** Completion does not advance to speaking; non-thinking and speech policy are separate gates. */
    @Synchronized internal fun finishLlmWork(ticket: LlmWorkTicket, result: LlmJobResult,
        verified: () -> Boolean = { false }): LlmJobResult {
        if (!llmWorkAllowed(ticket)) return LlmJobResult.CANCELLED
        val outcome = if (result == LlmJobResult.COMPLETED) {
            try { if (verified()) result else LlmJobResult.UNAVAILABLE }
            catch (_: Exception) { LlmJobResult.UNAVAILABLE }
        } else result
        if (!llmWorkAllowed(ticket)) return LlmJobResult.CANCELLED
        llmWork = null; ticket.cancelled = true
        if (outcome == LlmJobResult.UNAVAILABLE && !dispatch(ControllerEvent.FAILURE, failure = SafeError.UNAVAILABLE, token = ticket.token)) return LlmJobResult.CANCELLED
        return outcome
    }
    private var continuationToken: GenerationToken? = null
    private var continuationCancel: (() -> Unit)? = null
    @Synchronized internal fun prepareContinuation(token: GenerationToken, cancel: () -> Unit): Boolean {
        if (continuationToken === token || stopping || currentState !in setOf(ControllerState.THINKING, ControllerState.SPEAKING) || !accepts(token)) return false
        continuationToken = token; continuationCancel = cancel; return true
    }
    private val spokenClauses=mutableListOf<String>()
    private var spokenCardId="";private var spokenSuppressed=false
    private var spokenPresentationEnabled=false
    private var spokenOmitted=false;private var spokenInterrupted=false;private var spokenRevision=0L
    private fun bumpSpoken(){if(spokenRevision<9007199254740991L)spokenRevision++}
    private fun clearSpoken(resetSuppression:Boolean=true){if(resetSuppression)spokenSuppressed=false;spokenClauses.clear();spokenCardId="";spokenOmitted=false;spokenInterrupted=false;bumpSpoken()}
    @Synchronized fun setSpokenPresentationEnabled(enabled:Boolean){spokenPresentationEnabled=enabled;if(!enabled)clearSpoken(false)}
    @Synchronized internal fun markSpokenInterruption(){if(currentState!=ControllerState.ERROR || locked || stopping || spokenSuppressed)return;spokenClauses.clear();spokenCardId="";spokenOmitted=false;spokenInterrupted=true;spokenCardId=UUID.randomUUID().toString();bumpSpoken()}
    @Synchronized fun clearSpokenPresentation(){clearSpoken()}
    /** Visual dismissal has no audio cancellation or state transition authority. */
    @Synchronized fun dismissSpokenPresentation(session:String,epoch:Long,card:String,onlyIdle:Boolean=false):Boolean {
        if(locked || stopping || card.isEmpty() || session!=sessionId.toString() || epoch!=privacyEpoch || card!=spokenCardId || (onlyIdle && currentState !in setOf(ControllerState.STANDBY,ControllerState.ERROR)))return false
        clearSpoken(false);spokenSuppressed=true;return true
    }
    @Synchronized internal fun recordSpokenClause(ticket:SpeechWorkTicket,text:String){speechTransaction(ticket){
        if(!spokenPresentationEnabled || spokenSuppressed || text.isEmpty() || text.toByteArray(Charsets.UTF_8).size>1024 || text.contains('\u0000'))return@speechTransaction false
        spokenInterrupted=false;if(spokenCardId.isEmpty())spokenCardId=UUID.randomUUID().toString();spokenClauses+=text
        while(spokenClauses.size>32 || spokenClauses.sumOf{it.toByteArray(Charsets.UTF_8).size}>4096){spokenClauses.removeAt(0);spokenOmitted=true}
        bumpSpoken();true
    }}
    /** Volatile content is separate from the metadata snapshot and never logged. */
    @Synchronized fun spokenPresentation(allowed:Boolean):Map<String,Any>{
        if(!allowed || locked || stopping || !permissionGranted() || modelStatus()!=ModelStatus.READY || !((activeToken!=null && currentState in setOf(ControllerState.STANDBY,ControllerState.CAPTURING,ControllerState.THINKING,ControllerState.SPEAKING)) || (currentState==ControllerState.ERROR && spokenInterrupted)))return emptyMap()
        return mapOf("version" to 1,"sessionId" to sessionId.toString(),"operationId" to (activeToken?.operationId ?: stoppedOperationId).toString(),"generation" to generation,"privacyEpoch" to privacyEpoch,"revision" to spokenRevision,"cardId" to spokenCardId,"clauses" to spokenClauses.toList(),"interrupted" to spokenInterrupted,"earlierClausesOmitted" to spokenOmitted)
    }
    private var speechWork: SpeechWorkTicket? = null
    @Synchronized internal fun prepareSpeechWork(token: GenerationToken, cancel: () -> Unit, publish: (SpeechWorkTicket) -> Unit = {}): SpeechWorkTicket? {
        if (speechWork != null || stopping || speakerRequired || currentState !in setOf(ControllerState.THINKING, ControllerState.SPEAKING) || !accepts(token)) return null
        val ticket = SpeechWorkTicket(this, token, cancel)
        publish(ticket) // Initialize native receiver before cancellation can observe it.
        if (stopping || !accepts(token)) { ticket.cancelled = true; return null }
        speechWork = ticket; return ticket
    }
    /** Short native buffer/SDK scheduling transaction only; no IO, inference or joins. */
    @Synchronized internal fun speechTransaction(ticket: SpeechWorkTicket, action: () -> Boolean): Boolean {
        if (speechWork !== ticket || ticket.cancelled || stopping || speakerRequired || !accepts(ticket.token) || currentState !in setOf(ControllerState.THINKING, ControllerState.SPEAKING)) return false
        return try { action() && speechWork === ticket && !ticket.cancelled && accepts(ticket.token) } catch (_: Exception) { stop(); false }
    }
    @Synchronized internal fun speechStarted(ticket: SpeechWorkTicket): Boolean = speechTransaction(ticket) {
        clearIdle(); playback.begin(ticket.token); currentState = ControllerState.SPEAKING; true
    }
    @Synchronized internal fun speechGap(ticket: SpeechWorkTicket): Boolean = speechTransaction(ticket) {
        playback.finish(ticket.token); currentState = ControllerState.THINKING; true
    }
    /** Metadata access is native-only, default-denied, and serialized with privacy changes. */
    @Synchronized internal fun speechMetadata(ticket: SpeechWorkTicket, permitted: () -> Boolean, ledger: PlaybackLedger): List<PlaybackProgress> {
        if (ticket.token.privacyEpoch != privacyEpoch || locked) { ledger.clear(); return emptyList() }
        return if (permitted()) ledger.snapshot() else emptyList()
    }
    @Synchronized internal fun speechPrivacyCurrent(ticket: SpeechWorkTicket): Boolean = ticket.token.privacyEpoch == privacyEpoch && !locked
    @Synchronized internal fun finishSpeechWork(ticket: SpeechWorkTicket) {
        if (!speechTransaction(ticket) { true }) return
        speechWork = null; ticket.cancelled = true
        // A sealed empty queue ends the turn as well; this transition performs no SDK work.
        currentState = ControllerState.SPEAKING
        dispatch(ControllerEvent.PLAYBACK_FINISHED, token = ticket.token)
    }
    @Synchronized fun token(): GenerationToken? = activeToken
    private var vadCapture:VadCapturePermit?=null
    @Synchronized internal fun prepareVadCapture(permit:VadCapturePermit,capture:ControllerEffects,token:GenerationToken):Boolean {
        if(effects!==capture || !recognitionAllowed(token) || vadCapture?.active()==true || !permit.active())return false
        vadCapture=permit;return true
    }
    @Synchronized internal fun abandonVadCapture(permit:VadCapturePermit) { if(vadCapture===permit)vadCapture=null;permit.revoke() }
    /** Metadata only; accepted must enqueue native follow-up, never inference under this monitor. */
    @Synchronized internal fun finishVadCapture(permit:VadCapturePermit,token:GenerationToken,outcome:VadCaptureOutcome,active:()->Boolean,accepted:(VadCaptureOutcome)->Unit):Boolean {
        try {
            if(vadCapture!==permit || !permit.active() || !recognitionAllowed(token) || !active() || outcome.result !in listOf(EndpointResult.COMPLETE,EndpointResult.LIMIT,EndpointResult.NO_SPEECH,EndpointResult.INCOMPLETE) || outcome.totalSamples !in 0..480000 || outcome.lastChunkConsumed !in 0..minOf(1600,outcome.totalSamples))return false
            vadCapture=null;accepted(outcome);return true
        } finally { abandonVadCapture(permit) }
    }
    @Synchronized internal fun failVadCapture(permit:VadCapturePermit,token:GenerationToken,active:()->Boolean):Boolean {
        try {
            if(vadCapture!==permit || !permit.active() || !recognitionAllowed(token) || !active())return false
            return dispatch(ControllerEvent.FAILURE,SafeError.UNAVAILABLE,token)
        } finally { abandonVadCapture(permit) }
    }
    private fun revokeVadCapture(){val previous=vadCapture;vadCapture=null;previous?.revoke()}
    private fun invalidateGeneration(preserveSpoken:Boolean=false) {
        if(!preserveSpoken)clearSpoken()
        revokeVadCapture()
        interruptedCapture=null;independentCapture=null
        activeToken?.cancelled = true; activeToken = null; stoppedOperationId=UUID.randomUUID()
        val continuation = continuationCancel; continuationCancel = null; continuationToken = null
        try { continuation?.invoke() } catch (_: Exception) { diagnostics.record(SafeComponent.MODEL, SafeError.UNAVAILABLE, SafeSeverity.WARNING) }
        val speech = speechWork; speechWork = null; speech?.cancelled = true
        try { speech?.cancel?.invoke() } catch (_: Exception) { diagnostics.record(SafeComponent.SPEECH, SafeError.UNAVAILABLE, SafeSeverity.WARNING) }
        val previous = llmWork; llmWork = null
        if (previous != null) {
            previous.cancelled = true
            // Signal only: never join or destroy while holding this controller monitor.
            try { if (!previous.cancel()) diagnostics.record(SafeComponent.MODEL, SafeError.UNAVAILABLE, SafeSeverity.WARNING) }
            catch (_: LinkageError) { diagnostics.record(SafeComponent.MODEL, SafeError.UNAVAILABLE, SafeSeverity.WARNING) }
            catch (_: Exception) { diagnostics.record(SafeComponent.MODEL, SafeError.UNAVAILABLE, SafeSeverity.WARNING) }
        }
        if (generation == 9007199254740991L) { clearSpoken();sessionId = UUID.randomUUID(); generation = 0 } else generation++
    }
    private fun issueGeneration(preserveSpoken:Boolean=false) {
        invalidateGeneration(preserveSpoken)
        activeToken = GenerationToken(sessionId, UUID.randomUUID(), generation, privacyEpoch)
    }
    private fun accepts(token: GenerationToken?): Boolean {
        if (token == null || token !== activeToken || token.cancelled || token.privacyEpoch != privacyEpoch) return false
        if (!permissionGranted()) { stop(); return false }
        if(modelStatus()!=ModelStatus.READY) { modelsChanged();return false }
        return token === activeToken && !token.cancelled && token.privacyEpoch==privacyEpoch
    }
    private var currentState = ControllerState.STOPPED
    private var currentError: SafeError? = null
    /** Native pre-speech revalidation; this grants no model readiness or permissions. */
    @Synchronized internal fun canApproveSpeech(token:GenerationToken):Boolean = !stopping && !speakerRequired && currentState in listOf(ControllerState.THINKING,ControllerState.SPEAKING) && accepts(token)
    @Synchronized fun state(): ControllerState = currentState
    @Synchronized fun error(): SafeError? = currentError
    /** Native attachment check; call before acquiring capture/delivery locks. */
    @Synchronized internal fun canAttachWake(capture: ControllerEffects, token: GenerationToken): Boolean =
        effects === capture && currentState == ControllerState.STANDBY && accepts(token) && playback.allowsAudio()
    @Synchronized internal fun wakeCaptureFailed(token: GenerationToken, active: () -> Boolean): Boolean {
        if (!active()) return false
        return dispatch(ControllerEvent.FAILURE, failure = SafeError.UNAVAILABLE, token = token)
    }
    /** Revalidate the detector lease under the same monitor as token/state transitions. */
    @Synchronized internal fun wakeDetected(token:GenerationToken, active:()->Boolean):Boolean {
        if(!active() || !playback.allowsAudio()) return false
        return dispatch(ControllerEvent.SPEECH_DETECTED,token=token)
    }
    /** Final native recognition only, serialized with Stop. The accepted callback must only queue
     * native conversation work, without inference, store IO or capture locks in this monitor.
     * Unknown Moonshine confidence stays unknown; never synthesize a confidence score. */
    @Synchronized internal fun finishRecognition(token:GenerationToken, result:AsrText,
        confidence:Float?, ambiguous:Boolean=false, overlap:Boolean=false, active:()->Boolean,
        accepted:(String)->Unit):Boolean {
        if(!result.final || !recognitionAllowed(token))return false
        return try {
            if(!active() || !accepts(token))return false
            val decision=RecognitionPolicy.decide(result.text,confidence,ambiguous,overlap)
            if(!dispatch(ControllerEvent.ENDPOINT,token=token))return false
            when(decision){
                RecognitionDecision.Clarify->releaseSpeech(token,RecognitionPolicy.CLARIFICATION)
                is RecognitionDecision.Conversation->{accepted(decision.text);accepts(token)}
            }
        }catch(_:Exception){stop();false}
    }
    @Synchronized fun dispatch(event: ControllerEvent, failure: SafeError = SafeError.UNEXPECTED, token: GenerationToken? = null): Boolean {
        if (stopping && event != ControllerEvent.STOP) return false
        if (locked && event in setOf(ControllerEvent.START,ControllerEvent.RESUME)) return false
        if (event == ControllerEvent.STOP) return stop()
        if (event == ControllerEvent.RESUME && currentState != ControllerState.PAUSED) return false
        if (event == ControllerEvent.START && currentState == ControllerState.PAUSED) return false
        if (event == ControllerEvent.START || event == ControllerEvent.RESUME) return start()
        if (event in setOf(ControllerEvent.SPEECH_DETECTED, ControllerEvent.ENDPOINT, ControllerEvent.SPEECH_READY, ControllerEvent.PLAYBACK_FINISHED, ControllerEvent.FAILURE) && !accepts(token)) return false
        val next = nextState(currentState, event) ?: return false
        if(event==ControllerEvent.PLAYBACK_FINISHED && token!=null)playback.finish(token)
        if (event == ControllerEvent.START || event == ControllerEvent.SPEECH_DETECTED || event == ControllerEvent.PLAYBACK_FINISHED || event == ControllerEvent.RESUME) issueGeneration(event==ControllerEvent.PLAYBACK_FINISHED)
        if ((event == ControllerEvent.PAUSE || event == ControllerEvent.FAILURE) && !stop()) return false
        if(next!=ControllerState.CAPTURING)revokeVadCapture()
        currentState = next
        if (event == ControllerEvent.SPEECH_DETECTED) hasConversation=true
        try { updateIdle() } catch (_: Exception) { stop(); currentState=ControllerState.ERROR; currentError=SafeError.UNEXPECTED; return false }
        currentError = if (next == ControllerState.ERROR) failure else null
        if (next == ControllerState.ERROR) diagnostics.record(SafeComponent.CONTROLLER, failure, SafeSeverity.ERROR)
        return true
    }
    /** Recognized native command only; raw ASR text is neither retained nor bridged. */
    @Synchronized fun recognizedCommand(text: String, token: GenerationToken): Boolean {
        if (!accepts(token) || text.length > 64 || currentState !in setOf(ControllerState.STANDBY,ControllerState.CAPTURING,ControllerState.THINKING,ControllerState.SPEAKING)) return false
        return when (text.trim().lowercase(java.util.Locale.ROOT)) {
            "stop listening" -> stop()
            "end conversation" -> endConversation()
            else -> false
        }
    }
    @Synchronized fun endConversation(): Boolean {
        if (currentState !in setOf(ControllerState.STANDBY,ControllerState.CAPTURING,ControllerState.THINKING,ControllerState.SPEAKING)) return false
        return endSessionPreservingCapture()
    }
    @Synchronized fun privacyTransition(change: PrivacyChange): Boolean {
        privateGate.invalidate()
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
        return try { if (!privateGate.allows(effect) || !accepts(token)) return false; action(); accepts(token) && privateGate.allows(effect) && accepts(token) } catch (_: Exception) { stop(); currentState=ControllerState.ERROR; currentError=SafeError.UNEXPECTED; diagnostics.record(SafeComponent.MEMORY,SafeError.UNEXPECTED,SafeSeverity.ERROR); false }
    }
    @Synchronized fun releaseSpeech(token: GenerationToken, clause: String): Boolean {
        if (speakerRequired || !accepts(token) || currentState !in setOf(ControllerState.THINKING, ControllerState.SPEAKING)) return false
        clearIdle()
        return try {
            playback.begin(token);effects.playClause(clause)
            if (!accepts(token)) return false
            currentState = ControllerState.SPEAKING; true
        } catch (_: Exception) { stop(); currentState = ControllerState.ERROR; currentError = SafeError.UNEXPECTED; diagnostics.record(SafeComponent.SPEECH, SafeError.UNEXPECTED, SafeSeverity.ERROR); false }
    }
    @Synchronized fun cancelGeneration() {
        if (stopping) return
        if (!permissionGranted()) { stop(); return }
        val replyWasActive=currentState in setOf(ControllerState.THINKING,ControllerState.SPEAKING)
        invalidateGeneration()
        try { playback.cancel();effects.cancelWork() } catch (_: Exception) { stop(); currentState = ControllerState.ERROR; currentError = SafeError.UNEXPECTED; return }
        if (currentState in setOf(ControllerState.CAPTURING,ControllerState.THINKING,ControllerState.SPEAKING)) { currentState = ControllerState.STANDBY; issueGeneration();spokenInterrupted=replyWasActive;if(replyWasActive)spokenCardId=UUID.randomUUID().toString();bumpSpoken(); updateIdle() }
    }
    /** Cancel old work before creating the new turn; never reopen capture or revive a stopped run.
     * Verification is disk-free native echo-separated speech evidence, not an energy threshold. */
    @Synchronized internal fun interruptReply(token:GenerationToken,verified:()->Boolean):GenerationToken? {
        if(stopping || !accepts(token) || currentState !in setOf(ControllerState.THINKING,ControllerState.SPEAKING))return null
        return try {
            if(!verified() || !accepts(token))return null
            clearIdle();invalidateGeneration();playback.cancel()
            val expected=generation;val epoch=privacyEpoch
            effects.cancelWork()
            if(generation!=expected || privacyEpoch!=epoch || locked)return null
            if(!verified() || !permissionGranted() || modelStatus()!=ModelStatus.READY){stop();return null}
            issueGeneration();spokenInterrupted=true;spokenCardId=UUID.randomUUID().toString();bumpSpoken();currentState=ControllerState.CAPTURING;hasConversation=true;interruptedCapture=activeToken;independentCapture=verified;activeToken
        }catch(_:Exception){stop();null}
    }
    @Synchronized fun stop(): Boolean {
        privateGate.invalidate()
        if (stopping) return true
        stopping=true
        startIntent=null; capturePending=false; captureIntent=null
        clearIdle(); hasConversation=false;genericDialogue.clear()
        invalidateGeneration()
        currentState = ControllerState.STOPPED
        playback.cancel()
        currentError = null
        var failed = false
        for (cleanup in listOf(permission::cancelPendingRequests,effects::cancelWork, effects::releaseCapture, effects::clearVolatileContext)) {
            try { cleanup() } catch (_: Exception) { failed = true }
        }
        diagnostics.clear()
        if (failed) {
            currentState = ControllerState.ERROR; currentError = SafeError.UNEXPECTED
            diagnostics.record(SafeComponent.CONTROLLER, SafeError.UNEXPECTED, SafeSeverity.ERROR)
        }
        stopping=false
        return !failed
    }
    companion object {
        fun nextState(state: ControllerState, event: ControllerEvent): ControllerState? = when (event) {
            ControllerEvent.STOP -> ControllerState.STOPPED
            ControllerEvent.FAILURE -> ControllerState.ERROR
            ControllerEvent.SETUP_REQUIRED -> if (state == ControllerState.STOPPED) ControllerState.SETUP else null
            ControllerEvent.READY -> if (state in setOf(ControllerState.SETUP, ControllerState.ERROR)) ControllerState.STOPPED else null
            ControllerEvent.START -> if (state in setOf(ControllerState.STOPPED,ControllerState.PERMISSION_REQUIRED)) ControllerState.STANDBY else null
            ControllerEvent.SPEECH_DETECTED -> if (state == ControllerState.STANDBY) ControllerState.CAPTURING else null
            ControllerEvent.ENDPOINT -> if (state == ControllerState.CAPTURING) ControllerState.THINKING else null
            ControllerEvent.SPEECH_READY -> if (state == ControllerState.THINKING) ControllerState.SPEAKING else null
            ControllerEvent.PLAYBACK_FINISHED -> if (state == ControllerState.SPEAKING) ControllerState.STANDBY else null
            ControllerEvent.PAUSE -> if (state in setOf(ControllerState.STANDBY, ControllerState.CAPTURING, ControllerState.THINKING, ControllerState.SPEAKING)) ControllerState.PAUSED else null
            ControllerEvent.RESUME -> if (state == ControllerState.PAUSED) ControllerState.STANDBY else null
        }
    }
}
