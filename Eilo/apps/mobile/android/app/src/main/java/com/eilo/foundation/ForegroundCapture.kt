package com.eilo.foundation

import java.util.concurrent.Executor

/** Native-only PCM device. No file, network, JS or transcription consumer exists in this task. */
internal interface CaptureDevice {
    fun start()
    fun read(samples: ShortArray): Int
    fun close()
}

/** Process-owned lifecycle; opens on a native worker, reconciles every callback with a run ID. */
internal class ForegroundCapture(
    private val worker: Executor,
    private val eligible: () -> Boolean,
    private val open: () -> CaptureDevice,
    private val activate: () -> Unit = {},
    private val deactivate: () -> Unit = {},
    private val standby:StandbyAudioBuffer=StandbyAudioBuffer(),
) : ControllerEffects {
    private val monitor = Any()
    private var run = 0L
    @Volatile private var speechGain=1f
    override fun setOutputGain(gain:Float) { require(gain.isFinite() && gain in 0f..1f);speechGain=gain }
    private var device: CaptureDevice? = null
    private class WakeBinding(val controller: NativeController, val token: GenerationToken, val delivery: WakeFrameDelivery) {
        @Volatile var active = true
        fun close() { active = false; delivery.close() }
    }
    private var wake: WakeBinding? = null
    private var wakeEpoch = 0L

    /** Native-only attachment of a delivery already constructed on a native inference worker.
     * Never enqueue detector construction behind this executor's continuous capture loop.
     * The caller retains responsibility for closing a rejected candidate. No app/JS default calls it.
     */
    fun attachWakeDelivery(controller: NativeController, token: GenerationToken, delivery: WakeFrameDelivery): Boolean {
        val expected = synchronized(monitor) { run to wakeEpoch }
        if (delivery.sampleRate != 16000 || !delivery.belongsTo(token) || !controller.canAttachWake(this, token)) return false
        return synchronized(monitor) {
            if (run != expected.first || wakeEpoch != expected.second || device == null || wake != null || token.cancelled || !eligible()) false
            else { wake = WakeBinding(controller, token, delivery); true }
        }
    }
    private fun detachWake(): WakeBinding? = synchronized(monitor) { val previous = wake; previous?.active = false; wake = null; wakeEpoch++; previous }
    private fun drainWake(expected: Long) {
        val binding = synchronized(monitor) { if (run == expected) wake else null } ?: return
        // Never decode or call the controller while holding the capture monitor.
        when (val result = binding.delivery.drain()) {
            is WakeDrain.Events -> for (event in result.values) event.apply(binding.controller)
            WakeDrain.Failed -> binding.controller.wakeCaptureFailed(binding.token) { binding.active }
            WakeDrain.Inactive -> {
                synchronized(monitor) { if (wake === binding) wake = null }
                binding.close()
            }
        }
    }
    // There is no permission to open synchronously on a UI/permission callback thread.
    override fun startCapture() = false

    override fun beginCapture(completion: (Boolean) -> Unit, failure: () -> Unit) {
        val expected = synchronized(monitor) { check(device == null); standby.close(); ++run }
        worker.execute {
            var opened: CaptureDevice? = null
            val samples = ShortArray(320) // 20 ms at 16 kHz; reused and erased after bounded native retention.
            try {
                if (!current(expected) || !eligible()) { completion(false); return@execute }
                val activated = synchronized(monitor) { if (run != expected || !eligible()) false else { activate(); true } }
                if (!activated) { completion(false); return@execute }
                val candidate = open()
                opened = candidate
                val started = synchronized(monitor) {
                    if (run != expected || !eligible()) false
                    else { candidate.start(); device = candidate; true }
                }
                if (!started) { completion(false); return@execute }
                val bufferTicket=synchronized(monitor) { if(run==expected) standby.begin() else null }
                completion(true)
                while (current(expected)) {
                    // Nonblocking read and erase share the lifecycle monitor with Stop.
                    // No sample can remain in either application buffer across Stop's return.
                    val count = synchronized(monitor) {
                        if (run != expected) 0 else {
                            try {
                                standby.expire()
                                val read=candidate.read(samples)
                                if(read>0 && run==expected && eligible()) {
                                    if(bufferTicket!=null) standby.append(bufferTicket,samples,read)
                                    wake?.delivery?.submit(samples,read,16000)
                                }
                                read
                            } finally { samples.fill(0) }
                        }
                    }
                    if (count < 0 || !eligible()) throw IllegalStateException()
                    drainWake(expected)
                    Thread.sleep(10)
                }
            } catch (_: Exception) {
                if (current(expected)) failure()
            } finally {
                samples.fill(0)
                var abandonedWake: WakeBinding? = null
                val closeHere = synchronized(monitor) {
                    if (device === opened && run == expected) {
                        standby.close();device=null; ++run; abandonedWake=wake;abandonedWake?.active=false;wake=null;wakeEpoch++;true
                    } else device !== opened
                }
                abandonedWake?.close()
                // Device close is idempotent, including races with Stop.
                if (closeHere) try { opened?.close() } catch (_: Exception) { if (current(expected)) failure() }
            }
        }
    }

    private fun current(expected: Long) = synchronized(monitor) { run == expected }
    override fun releaseCapture() {
        val (previous, binding) = synchronized(monitor) {
            ++run; standby.close(); val value=device; device=null; val attached=wake;attached?.active=false;wake=null;wakeEpoch++;value to attached
        }
        try { binding?.close() } finally { try { previous?.close() } finally { deactivate() } }
    }
    override fun cancelWork() { detachWake()?.close() }
    override fun clearVolatileContext() {
        val binding = synchronized(monitor) { standby.clear(); val previous=wake;previous?.active=false;wake=null;wakeEpoch++;previous }
        binding?.close()
    }
    override fun playClause(clause: String) { throw IllegalStateException() } // TTS belongs to S06.
}
