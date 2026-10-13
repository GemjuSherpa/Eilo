package com.eilo.foundation
import java.util.UUID

/** Metadata only. SDK events do not establish that anyone heard the output. */
internal data class PlaybackProgress(val clauseId: UUID, val produced: Boolean = true, val queued: Boolean = true,
    val sdkStarted: Boolean = false, val sdkFinished: Boolean = false, val interruptionRequested: Boolean = false,
    val sdkInterrupted: Boolean = false, val failed: Boolean = false, val discardedBeforeStart: Boolean = false)
/** Controller-confined, volatile bounded ledger. No text, audio, wall clock or persistence. */
internal class PlaybackLedger {
    private val records = ArrayList<PlaybackProgress>()
    fun produced(id: UUID) { if (records.size == 32) records.removeAt(0); records.add(PlaybackProgress(id)) }
    fun event(id: UUID, event: OfflineSpeechEvent) { update(id) { when(event) {
        OfflineSpeechEvent.STARTED -> it.copy(sdkStarted = true)
        OfflineSpeechEvent.FINISHED -> it.copy(sdkFinished = true)
        OfflineSpeechEvent.INTERRUPTED -> it.copy(sdkInterrupted = true)
        OfflineSpeechEvent.FAILED -> it.copy(failed = true)
    } } }
    fun cancel(active: UUID?, waiting: List<UUID>) {
        if (active != null) update(active) { it.copy(interruptionRequested = !it.sdkFinished && !it.sdkInterrupted) }
        waiting.forEach { id -> update(id) { it.copy(discardedBeforeStart = true) } }
    }
    private fun update(id: UUID, change: (PlaybackProgress) -> PlaybackProgress) { val i=records.indexOfFirst{it.clauseId==id};if(i>=0)records[i]=change(records[i]) }
    fun snapshot(): List<PlaybackProgress> = records.toList()
    fun clear() = records.clear()
}
