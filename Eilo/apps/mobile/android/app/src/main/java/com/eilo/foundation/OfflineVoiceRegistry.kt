package com.eilo.foundation

import java.util.UUID

internal data class OfflineVoice(val id: String, val language: String, val installed: Boolean,
    val networkRequired: Boolean?, val offlineVerified: Boolean = false)
internal data class OfflineVoiceSelection(val voice: OfflineVoice, val epoch: UUID)

/** Native observed registry only. Unknown network capability needs an explicit offline
 * verification record for the exact installed voice/OS build; never infer from quality.
 * Refresh on a platform worker. Controller reads use this bounded volatile snapshot.
 */
internal class OfflineVoiceRegistry {
    private var epoch = UUID.randomUUID()
    private var selected: OfflineVoice? = null
    @Synchronized fun refresh(voices: List<OfflineVoice>, requested: String? = null): Boolean {
        epoch = UUID.randomUUID(); selected = null
        if (voices.size > 128 || requested?.length ?: 0 > 256) return false
        val eligible = voices.filter { eligible(it) }
        if (eligible.map { it.id }.toSet().size != eligible.size) return false
        selected = if (requested != null) eligible.singleOrNull { it.id == requested } else eligible.sortedBy { it.id }.firstOrNull()
        return selected != null
    }
    @Synchronized fun selection() = selected?.let { OfflineVoiceSelection(it, epoch) }
    @Synchronized fun current(selection: OfflineVoiceSelection) = selection.epoch == epoch && selection.voice == selected
    @Synchronized fun invalidate() { epoch = UUID.randomUUID(); selected = null }
    @Synchronized fun ready() = selected != null
    private fun eligible(v: OfflineVoice) = v.id.matches(Regex("[A-Za-z0-9_.:-]{1,256}")) &&
        v.language.matches(Regex("(?i)en(?:-[a-z0-9]{2,8})*")) && v.installed &&
        (v.networkRequired == false || v.networkRequired == null && v.offlineVerified)
}
internal class VoiceAwareReadiness(private val models: ModelReadinessAdapter, private val voices: OfflineVoiceRegistry) : ModelReadinessAdapter {
    override fun status(): ModelStatus {
        val status = models.status()
        return if (status != ModelStatus.READY) status else if (voices.ready()) status else ModelStatus.OFFLINE_VOICE_MISSING
    }
}
