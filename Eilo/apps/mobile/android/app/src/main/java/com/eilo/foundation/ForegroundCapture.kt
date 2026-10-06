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
) : ControllerEffects {
    private val monitor = Any()
    private var run = 0L
    private var device: CaptureDevice? = null
    // There is no permission to open synchronously on a UI/permission callback thread.
    override fun startCapture() = false

    override fun beginCapture(completion: (Boolean) -> Unit, failure: () -> Unit) {
        val expected = synchronized(monitor) { check(device == null); ++run }
        worker.execute {
            var opened: CaptureDevice? = null
            val samples = ShortArray(320) // 20 ms at 16 kHz; reused, never retained.
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
                completion(true)
                while (current(expected)) {
                    // Nonblocking read and erase share the lifecycle monitor with Stop.
                    // No sample can remain in the application buffer across Stop's return.
                    val count = synchronized(monitor) {
                        if (run != expected) 0 else {
                            try { candidate.read(samples) } finally { samples.fill(0) }
                        }
                    }
                    if (count < 0 || !eligible()) throw IllegalStateException()
                    Thread.sleep(10)
                }
            } catch (_: Exception) {
                if (current(expected)) failure()
            } finally {
                samples.fill(0)
                val closeHere = synchronized(monitor) {
                    if (device === opened && run == expected) { device=null; ++run; true }
                    else device !== opened
                }
                // Device close is idempotent, including races with Stop.
                if (closeHere) try { opened?.close() } catch (_: Exception) { if (current(expected)) failure() }
            }
        }
    }

    private fun current(expected: Long) = synchronized(monitor) { run == expected }
    override fun releaseCapture() {
        val previous = synchronized(monitor) { ++run; val value=device; device=null; value }
        try { previous?.close() } finally { deactivate() }
    }
    override fun cancelWork() {}
    override fun clearVolatileContext() {} // read buffer is erased on every read, including failure.
    override fun playClause(clause: String) { throw IllegalStateException() } // TTS belongs to S06.
}
