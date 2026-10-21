package com.eilo.foundation

import java.lang.ref.WeakReference
import java.util.UUID

internal class SpeechWorkTicket(val controller: NativeController, val token: GenerationToken, val cancel: () -> Unit) {
    var cancelled = false // Access only under the controller monitor.
}
/** Sink methods must only schedule SDK work; never block or join. */
internal interface NativeClauseSink {
    fun enqueue(token: GenerationToken, text: String, event: (OfflineSpeechEvent) -> Unit): Boolean
    fun cancel()
}
internal class AndroidClauseSink(private val speech: AndroidOfflineSpeech) : NativeClauseSink {
    override fun enqueue(token: GenerationToken, text: String, event: (OfflineSpeechEvent) -> Unit) = speech.enqueue(token, text, event = event)
    override fun cancel() = speech.cancel()
}
/** Bounded natural-clause input, one active + four waiting clauses, 1024 UTF-8 bytes each.
 * Caller owns this native queue until sealed/cancelled. No ordinary app caller exists.
 * Authorization is denied by default; S07 supplies the separate pre-speech policy.
 * Mutable queue state and callbacks are serialized by the controller transaction.
 * Clearing references does not certify immutable String or SDK memory erasure.
 */
internal class NativeClauseQueue private constructor(
    private val controller: NativeController, private val sink: NativeClauseSink, private val scheduler: IdleScheduler,
    private val authorized: (GenerationToken, String) -> Boolean,
    private val completed:(GenerationToken)->Unit, private val cleared:()->Unit,
) {
    private class Clause(text: String) { val id = UUID.randomUUID(); var text: String? = text; var completedText:String?=null; var timeout: IdleCancellation? = null }
    private lateinit var ticket: SpeechWorkTicket
    private val ledger = PlaybackLedger()
    private val waiting = ArrayDeque<Clause>()
    private var active: Clause? = null
    private var fragment = ""
    private var sealed = false
    private var closed = false
    companion object {
        private val timers = NativeIdleScheduler()
        fun create(controller: NativeController, token: GenerationToken, sink: NativeClauseSink,
            scheduler: IdleScheduler = timers, completed:(GenerationToken)->Unit={},cleared:()->Unit={},authorized: (GenerationToken, String) -> Boolean = { _, _ -> false }): NativeClauseQueue? {
            val queue = NativeClauseQueue(controller, sink, scheduler, authorized,completed,cleared); val weak = WeakReference(queue)
            queue.ticket = controller.prepareSpeechWork(token, cancel = { weak.get()?.clear() }, publish = { queue.ticket = it }) ?: return null
            return queue
        }
    }
    fun enqueue(text: String): Boolean = controller.speechTransaction(ticket) {
        if (closed || sealed) return@speechTransaction false
        if (text.isBlank() || text.toByteArray(Charsets.UTF_8).size > 1024 || text.any { it == '\u0000' } || waiting.size >= 4 || !authorized(ticket.token, text)) {
            fail(); return@speechTransaction false
        }
        if (closed || ticket.cancelled || !controller.canApproveSpeech(ticket.token)) return@speechTransaction false
        val clause = Clause(text); ledger.produced(clause.id); waiting.addLast(clause); pump(); !closed
    }
    /** Decoded, policy-approved text fragments only. Hold punctuation until whitespace,
     * so a split decimal/token does not force a premature clause. Never truncate text. */
    fun append(text: String): Boolean = controller.speechTransaction(ticket) {
        if (closed || sealed) return@speechTransaction false
        if (text.toByteArray(Charsets.UTF_8).size > 1024 || text.contains('\u0000')) { fail(); return@speechTransaction false }
        for (character in text) {
            if (character.isWhitespace() && fragment.lastOrNull() in listOf('.', '!', '?', ';', ':')) {
                val clause = fragment.trim(); fragment = ""
                if (!enqueue(clause)) return@speechTransaction false
            }
            fragment += character
            if (fragment.toByteArray(Charsets.UTF_8).size > 1024) { fail(); return@speechTransaction false }
            if (character == '\n' && fragment.isNotBlank()) {
                val clause = fragment.trim(); fragment = ""
                if (!enqueue(clause)) return@speechTransaction false
            }
        }
        true
    }
    fun seal(): Boolean {
        var accepted = false
        controller.speechTransaction(ticket) {
            if (closed || sealed) return@speechTransaction false
            if (fragment.isNotBlank()) { val clause = fragment.trim(); fragment = ""; if (!enqueue(clause)) return@speechTransaction false }
            fragment = ""; sealed = true; accepted = true; pump(); true
        }
        return accepted
    }
    private fun pump() {
        if (closed || active != null) return
        if (waiting.isEmpty()) { if (sealed) { closed = true;completed(ticket.token); controller.finishSpeechWork(ticket) }; return }
        val clause = waiting.removeFirst(); active = clause
        val weak = WeakReference(this)
        try { clause.timeout = scheduler.schedule(60_000) { weak.get()?.event(clause, OfflineSpeechEvent.FAILED) } }
        catch (_: Exception) { fail(); return }
        if (closed || active !== clause) { clause.timeout?.cancel(); clause.timeout = null; return }
        val text = clause.text; clause.text = null;clause.completedText=text
        if (text == null || !authorized(ticket.token, text) || closed || ticket.cancelled || !controller.canApproveSpeech(ticket.token) || !sink.enqueue(ticket.token, text) { event(clause, it) }) {
            if (active === clause) fail()
        }
    }
    private fun event(clause: Clause, event: OfflineSpeechEvent) {
        controller.speechTransaction(ticket) {
            if (closed || active !== clause) return@speechTransaction false
            if (event != OfflineSpeechEvent.STARTED) { clause.timeout?.cancel(); clause.timeout = null }
            ledger.event(clause.id, event)
            when (event) {
                OfflineSpeechEvent.STARTED -> controller.speechStarted(ticket)
                OfflineSpeechEvent.FINISHED -> { clause.completedText?.let{controller.recordSpokenClause(ticket,it)};clause.completedText=null;active = null; controller.speechGap(ticket); pump(); true }
                OfflineSpeechEvent.INTERRUPTED -> { fail();controller.markSpokenInterruption();false }
                else -> { fail(); false }
            }
        }
    }
    private fun fail() { clear(); controller.dispatch(ControllerEvent.FAILURE, failure = SafeError.UNAVAILABLE, token = ticket.token) }
    private fun clear() { ledger.cancel(active?.id, waiting.map { it.id }); if (!controller.speechPrivacyCurrent(ticket)) ledger.clear(); closed = true; fragment = ""; active?.timeout?.cancel(); active?.timeout = null; active?.text = null;active?.completedText=null; active = null; waiting.forEach { it.text = null }; waiting.clear();cleared(); sink.cancel() }
    fun progress(permitted: () -> Boolean = { false }): List<PlaybackProgress> = controller.speechMetadata(ticket, permitted, ledger)
    fun cancel() { controller.speechTransaction(ticket) { controller.cancelGeneration(); true } }
}
