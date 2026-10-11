package com.eilo.foundation

/** Synchronous native inference-worker operation, never the capture executor, UI or JS.
 * Mint the ticket before scheduling. Capture owns successful delivery; every rejected/failed
 * candidate closes here. No default app caller, runtime loader or readiness override is installed.
 */
internal object WakeCaptureInstaller {
    fun install(
        ticket: ForegroundCapture.WakeSetupTicket, store: PackStore, selection: WakePackSelection,
        configuration: WakeConfiguration, api: NativeWakeAPI=NativeWakeAPI.unavailable,
    ): Boolean {
        var lease: WakePackLease?=null
        var detector: WakeDetector?=null
        var delivery: WakeFrameDelivery?=null
        var attached=false
        try {
            if (!ticket.capture.currentWakeSetup(ticket) || !ticket.controller.canAttachWake(ticket.capture,ticket.token)) return false
            val verifiedPack=WakePackLease.resolve(store,selection);lease=verifiedPack
            if (!ticket.capture.currentWakeSetup(ticket)) return false
            detector=WakeDetector(configuration,verified=verifiedPack::verified,open={ config ->
                val stream=verifiedPack.openStream(config,api)
                object : WakeKeywordStream by stream {
                    override fun close() { try { stream.close() } finally { verifiedPack.close() } }
                }
            })
            delivery=WakeFrameDelivery(16000,detector,ticket.token)
            if (!verifiedPack.verified()) return false
            attached=ticket.capture.attachWakeDelivery(ticket,delivery)
            return attached
        } catch (_: Exception) {
            return false // No raw causes, paths or content leave this native operation.
        } finally {
            if (!attached) {
                try { delivery?.close() ?: detector?.close() } finally { lease?.close() }
            }
        }
    }
}
