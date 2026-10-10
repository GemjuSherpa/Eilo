package com.eilo.foundation

/** Native reviewed configuration, never derived from manifest order or supplied by JavaScript. */
internal data class WakeArtifactPin(val id: String, val sha256: String) {
    init {
        require(id.matches(Regex("[a-z0-9][a-z0-9-]{0,63}")))
        require(sha256.matches(Regex("[a-f0-9]{64}")))
    }
}
internal data class WakePackSelection(
    val packId: String, val runtimeRevision: String,
    val encoder: WakeArtifactPin, val decoder: WakeArtifactPin,
    val joiner: WakeArtifactPin, val tokens: WakeArtifactPin,
) {
    init {
        require(packId.matches(Regex("[a-z0-9][a-z0-9-]{0,63}")))
        require(runtimeRevision.matches(Regex("[a-f0-9]{40}")))
        require(listOf(encoder,decoder,joiner,tokens).map { it.id }.toSet().size==4)
    }
}

/** Resolve on the installer/inference worker. Borrow-time checks are revocable, disk-free leases.
 * Store slots must remain app-private and immutable; this does not detect arbitrary external file
 * mutation between checks. On known corruption/maintenance, revoke before changing any files.
 * Closing revokes use; the caller still closes its exclusively owned decoder/delivery.
 */
internal class WakePackLease private constructor(
    private val store: PackStore, private val epoch: java.util.UUID,
    private val paths: WakeModelPaths,
) {
    @Volatile private var active=true
    fun verified(): Boolean = active && store.epoch()==epoch
    fun close() { active=false }
    fun openStream(configuration: WakeConfiguration, api: NativeWakeAPI=NativeWakeAPI.unavailable): NativeWakeStream =
        NativeWakeStream(paths,configuration,::verified,api)

    companion object {
        fun resolve(store: PackStore, selection: WakePackSelection): WakePackLease {
            val epoch=store.epoch()
            val snapshot=store.verifiedFiles() ?: error("unavailable") // Signature, runtime, licenses and every file hash.
            val pack=snapshot.first
            check(pack.manifest.packId==selection.packId && pack.manifest.runtimeRevision==selection.runtimeRevision)
            val pins=listOf(selection.encoder,selection.decoder,selection.joiner,selection.tokens)
            val files=pins.mapIndexed { position,pin ->
                val index=pack.manifest.artifacts.indexOfFirst { it.id==pin.id }
                check(index>=0)
                val artifact=pack.manifest.artifacts[index]
                check(artifact.sha256==pin.sha256)
                check(artifact.role==if(position==3) "tokenizer" else "wake")
                check(artifact.filename.endsWith(if(position==3) ".txt" else ".onnx"))
                snapshot.second[index].absolutePath
            }
            check(store.epoch()==epoch) // Reject a replacement even when the selected digest is unchanged.
            return WakePackLease(store,epoch,WakeModelPaths(files[0],files[1],files[2],files[3]))
        }
    }
}
