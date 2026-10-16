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
    private var vadSlot:VadCaptureSlot?=null
    private var device: CaptureDevice? = null
    private class WakeBinding(val controller: NativeController, val token: GenerationToken, val delivery: WakeFrameDelivery) {
        @Volatile var active = true
        fun close() { active = false; delivery.close() }
    }
    private var wake: WakeBinding? = null
    private var wakeEpoch = 0L

    /** Mint before scheduling expensive construction on a separate inference worker. */
    internal class WakeSetupTicket internal constructor(
        internal val capture: ForegroundCapture, internal val controller: NativeController,
        internal val token: GenerationToken, internal val run: Long, internal val epoch: Long,
    )
    fun prepareWakeSetup(controller: NativeController, token: GenerationToken): WakeSetupTicket? {
        if (!controller.canAttachWake(this,token)) return null
        return synchronized(monitor) {
            if (device==null || wake!=null || token.cancelled || !eligible()) null
            else WakeSetupTicket(this,controller,token,run,wakeEpoch)
        }
    }
    fun currentWakeSetup(ticket: WakeSetupTicket): Boolean = synchronized(monitor) {
        ticket.capture===this && run==ticket.run && wakeEpoch==ticket.epoch &&
            device!=null && wake==null && !ticket.token.cancelled && eligible()
    }
    /** Native-only preconstructed delivery; rejected candidates remain caller-owned. */
    fun attachWakeDelivery(controller: NativeController, token: GenerationToken, delivery: WakeFrameDelivery): Boolean {
        val ticket=prepareWakeSetup(controller,token) ?: return false
        return attachWakeDelivery(ticket,delivery)
    }
    fun attachWakeDelivery(ticket: WakeSetupTicket, delivery: WakeFrameDelivery): Boolean {
        if (ticket.capture!==this || delivery.sampleRate!=16000 || !delivery.belongsTo(ticket.token) ||
            !delivery.available() || !ticket.controller.canAttachWake(this,ticket.token)) return false
        return synchronized(monitor) {
            if (!currentWakeSetup(ticket) || !delivery.available()) false
            else { wake=WakeBinding(ticket.controller,ticket.token,delivery);wakeEpoch++;true }
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
                    else { candidate.start(); device = candidate; vadSlot=VadCaptureSlot(16000); true }
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
                                    vadSlot?.submit(samples,read,16000)
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
                var abandonedVad:VadCaptureSlot?=null
                val closeHere = synchronized(monitor) {
                    if (device === opened && run == expected) {
                        standby.close();device=null;abandonedVad=vadSlot;vadSlot=null; ++run; abandonedWake=wake;abandonedWake?.active=false;wake=null;wakeEpoch++;true
                    } else device !== opened
                }
                abandonedWake?.close();abandonedVad?.close()
                // Device close is idempotent, including races with Stop.
                if (closeHere) try { opened?.close() } catch (_: Exception) { if (current(expected)) failure() }
            }
        }
    }

    /** Call on a dedicated serial native inference worker, never on the recorder executor/UI.
     * Explicit verified native-only capability/API; no default app caller or runtime loading. */
    fun connectVad(controller:NativeController,token:GenerationToken,inferenceWorker:Executor,
        model:String,verified:()->Boolean,api:NativeVadApi=UnavailableVadApi,
        accepted:(VadCaptureOutcome)->Unit={},openAsr:((()->Boolean)->AsrStream)?=null,
        recognized:(AsrText)->Unit={},asrVerified:()->Boolean={false}):Boolean {
        val slot=synchronized(monitor){if(!eligible())null else vadSlot} ?: return false
        return slot.install(this,controller,token,inferenceWorker,verified,
            open={check->NativeVadStream(model,check,api)},accepted=accepted,openAsr=openAsr,recognized=recognized,asrVerified=asrVerified)
    }

    /** Mint on the caller before scheduling SpeechCaptureInstaller on the serial inference worker. */
    fun prepareSpeechSetup(controller:NativeController,token:GenerationToken):VadCaptureSlot.SetupTicket? {
        val snapshot=synchronized(monitor){if(!eligible())null else vadSlot?.let{it to run}} ?: return null
        return snapshot.first.prepare(this,controller,token,{current(snapshot.second) && eligible()})
    }

    private fun current(expected: Long) = synchronized(monitor) { run == expected }
    override fun releaseCapture() {
        val (previous, binding, vad) = synchronized(monitor) {
            ++run; standby.close(); val value=device; device=null; val attached=wake;attached?.active=false;wake=null;wakeEpoch++;val v=vadSlot;vadSlot=null;Triple(value,attached,v)
        }
        try { vad?.close();binding?.close() } finally { try { previous?.close() } finally { deactivate() } }
    }
    override fun cancelWork() { val v=synchronized(monitor){vadSlot};v?.detach();detachWake()?.close() }
    override fun clearVolatileContext() {
        val binding = synchronized(monitor) { standby.clear(); val previous=wake;previous?.active=false;wake=null;wakeEpoch++;previous }
        val v=synchronized(monitor){vadSlot};v?.detach();binding?.close()
    }
    override fun playClause(clause: String) { throw IllegalStateException() } // TTS belongs to S06.
}
