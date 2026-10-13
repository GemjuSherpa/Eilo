package com.eilo.foundation

import android.content.Context
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.UUID
import java.util.concurrent.Executor
import java.util.concurrent.Executors
import java.util.concurrent.ExecutorService
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

internal enum class OfflineSpeechEvent { STARTED, FINISHED, INTERRUPTED, FAILED }
internal interface AndroidSpeechBackend {
    fun voices(): List<OfflineVoice>
    fun listener(receive: (String, OfflineSpeechEvent) -> Unit)
    fun start(id: String, text: String, voice: OfflineVoice, rate: Float, gain: Float): Boolean
    fun stop()
    fun shutdown()
}

/** Explicit native construction only. No setLanguage, download prompt, network voice,
 * file synthesis or raw-text callback/logging. SDK/engine internal retention is unverified.
 */
internal class AndroidSystemSpeech(context: Context) : AndroidSpeechBackend {
    private val initialized = AtomicBoolean(false)
    private val tts = TextToSpeech(context.applicationContext) { initialized.set(it == TextToSpeech.SUCCESS) }
    @Volatile private var receive: (String, OfflineSpeechEvent) -> Unit = { _, _ -> }
    init { tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
        override fun onStart(id: String) { receive(id, OfflineSpeechEvent.STARTED) }
        override fun onDone(id: String) { receive(id, OfflineSpeechEvent.FINISHED) }
        override fun onError(id: String) { receive(id, OfflineSpeechEvent.FAILED) }
        override fun onError(id: String, errorCode: Int) { receive(id, OfflineSpeechEvent.FAILED) }
        override fun onStop(id: String, interrupted: Boolean) { receive(id, OfflineSpeechEvent.INTERRUPTED) }
    }) }
    override fun listener(receive: (String, OfflineSpeechEvent) -> Unit) { this.receive = receive }
    override fun voices(): List<OfflineVoice> = try {
        if (!initialized.get()) emptyList() else (tts.voices ?: emptySet()).filter { it.locale.language == "en" }.take(129).map {
            OfflineVoice(it.name, it.locale.toLanguageTag(), !it.features.contains(TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED), it.isNetworkConnectionRequired)
        }
    } catch (_: Exception) { emptyList() }
    override fun start(id: String, text: String, voice: OfflineVoice, rate: Float, gain: Float): Boolean = try {
        val selected = tts.voices?.singleOrNull { it.name == voice.id && !it.isNetworkConnectionRequired &&
            !it.features.contains(TextToSpeech.Engine.KEY_FEATURE_NOT_INSTALLED) && it.locale.language == "en" }
        initialized.get() && selected != null && tts.setVoice(selected) == TextToSpeech.SUCCESS &&
            tts.setSpeechRate(rate) == TextToSpeech.SUCCESS &&
            tts.speak(text, TextToSpeech.QUEUE_FLUSH, Bundle().apply { putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, gain) }, id) == TextToSpeech.SUCCESS
    } catch (_: Exception) { false }
    override fun stop() { check(tts.stop() == TextToSpeech.SUCCESS) }
    override fun shutdown() { initialized.set(false); receive = { _, _ -> }; tts.shutdown() }
}

/** One current clause; the later native clause queue supplies bounded ordered work.
 * All SDK calls/events run on the separate serial worker. Cancel revokes immediately
 * and schedules SDK stop without joining under the controller. Actual audio-stop timing
 * and engine persistence/network behavior require physical tests.
 */
internal class AndroidOfflineSpeech(
    private val backend: AndroidSpeechBackend,
    val registry: OfflineVoiceRegistry = OfflineVoiceRegistry(),
    private val allowed: (GenerationToken) -> Boolean = { false },
    private val worker: Executor = Executors.newSingleThreadExecutor { Thread(it, "eilo-offline-speech").apply { isDaemon = true } },
    private val scheduler: IdleScheduler = timers,
) {
    companion object { private val timers = NativeIdleScheduler() }
    private class Request(val token: GenerationToken, val voice: OfflineVoiceSelection, text: String,
        val rate: Float, val gain: Float, val event: (OfflineSpeechEvent) -> Unit) {
        val id = UUID.randomUUID().toString()
        val text = AtomicReference<String?>(text)
    }
    private val active = AtomicReference<Request?>()
    private val closed = AtomicBoolean(false)
    private class Preparation(val requested: String?, val complete: (Boolean) -> Unit) {
        var done = false; var timeout: IdleCancellation? = null
    }
    private val preparationGate = Any()
    private var preparing: Preparation? = null
    private fun finishPreparation(request: Preparation, voices: List<OfflineVoice>?) {
        val ready = synchronized(preparationGate) {
            if (preparing !== request || request.done) return
            val value = !closed.get() && voices != null && registry.refresh(voices, request.requested)
            if (!value) registry.invalidate()
            request.done = true; preparing = null; request.timeout?.cancel(); value
        }
        try { request.complete(ready) } catch (_: Exception) { registry.invalidate() }
    }
    private fun cancelPreparation() {
        replacePreparation(null)
    }
    private fun replacePreparation(next: Preparation?) {
        val old = synchronized(preparationGate) {
            val old = preparing; preparing = next
            old?.done = true; old?.timeout?.cancel()
            if (old != null) registry.invalidate()
            old
        }
        try { old?.complete?.invoke(false) } catch (_: Exception) { registry.invalidate() }
    }
    init { backend.listener { id, event -> post { deliver(id, event) } } }
    /** Native preparation on the worker; false is unavailable, never fallback. */
    fun refresh(requested: String? = null, complete: (Boolean) -> Unit) {
        if (closed.get()) { complete(false); return }
        val request = Preparation(requested, complete)
        replacePreparation(request)
        val timeout = try { scheduler.schedule(5000) { finishPreparation(request, null) } }
            catch (_: Exception) { finishPreparation(request, null); return }
        synchronized(preparationGate) { if (request.done) timeout.cancel() else request.timeout = timeout }
        if (!post {
            if (synchronized(preparationGate) { request.done || preparing !== request }) return@post
            val voices = try {
                val old = active.getAndSet(null)
                if (old != null) { old.text.set(null); backend.stop() }
                backend.voices()
            } catch (_: Exception) { null }
            finishPreparation(request, voices)
        }) finishPreparation(request, null)
    }
    fun enqueue(token: GenerationToken, text: String, rate: Float = 1f, gain: Float = 1f,
        event: (OfflineSpeechEvent) -> Unit): Boolean {
        if (closed.get() || token.cancelled || text.isBlank() || text.toByteArray(Charsets.UTF_8).size > 4096 ||
            !rate.isFinite() || rate !in 0.5f..1.5f || !gain.isFinite() || gain !in 0f..1f) return false
        val selection = registry.selection() ?: return false
        if (!currentToken(token)) return false
        val request = Request(token, selection, text, rate, gain, event)
        if (!active.compareAndSet(null, request)) return false
        return post {
            if (!current(request)) { abandon(request); return@post }
            val clause = request.text.getAndSet(null) ?: return@post
            val started = try { backend.start(request.id, clause, selection.voice, rate, gain) } catch (_: Exception) { false }
            if (!started) deliver(request.id, OfflineSpeechEvent.FAILED)
            if (!current(request)) { abandon(request); backend.stop() }
        }.also { if (!it) abandon(request) }
    }
    private fun currentToken(token: GenerationToken) = !token.cancelled && try { allowed(token) } catch (_: Exception) { false }
    private fun current(r: Request) = !closed.get() && active.get() === r && registry.current(r.voice) && currentToken(r.token)
    private fun abandon(r: Request) { r.text.set(null); active.compareAndSet(r, null) }
    private fun deliver(id: String, event: OfflineSpeechEvent) {
        val r = active.get() ?: return
        if (r.id != id) return
        if (!current(r)) { abandon(r); return }
        if (event != OfflineSpeechEvent.STARTED) abandon(r)
        try { r.event(event) } catch (_: Exception) { cancel() }
    }
    fun cancel() {
        cancelPreparation()
        active.getAndSet(null)?.text?.set(null)
        post { try { backend.stop() } catch (_: Exception) { registry.invalidate() } }
    }
    fun close() {
        if (!closed.compareAndSet(false, true)) return
        cancelPreparation()
        active.getAndSet(null)?.text?.set(null); registry.invalidate()
        post { try { backend.stop() } finally { backend.shutdown() } }
        (worker as? ExecutorService)?.shutdown() // Injected workers must also be exclusively owned.
    }
    private fun post(action: () -> Unit): Boolean = try {
        worker.execute { try { action() } catch (_: Exception) { registry.invalidate(); active.getAndSet(null)?.text?.set(null) } }; true
    } catch (_: Exception) { registry.invalidate(); false }
}
