package com.eilo.foundation

internal class WakeCaptureActivation(private val activation: WakeActivation, private val lease: WakeLease) {
    fun apply(controller: NativeController) = activation.apply(controller) { lease.active }
}

internal sealed class WakeDrain {
    class Events(val values: List<WakeCaptureActivation>) : WakeDrain()
    object Failed : WakeDrain()
    object Inactive : WakeDrain()
}

/** Four native PCM16 frames, each <=100 ms, with <250 ms receive age.
 * Construct/drain on a serialized native worker. Submit only copies; it never decodes or dispatches.
 * This exclusively owns its detector. Verification/clock callbacks must not acquire controller or
 * capture locks. Apply returned metadata only after drain releases its locks.
 */
internal class WakeFrameDelivery(
    val sampleRate: Int,
    private val detector: WakeDetector,
    private val token: GenerationToken,
    private val now: () -> Long = System::nanoTime,
) {
    private val queue = Any()
    private val consumer = Any()
    private val capacity: Int
    private val storage: ShortArray
    private val scratch: ShortArray
    private val counts = IntArray(4)
    private val times = LongArray(4)
    private var head = 0
    private var size = 0
    private var open = true
    private var failed = false
    private var reported = false
    private var lastClock: Long? = null
    private val lease = WakeLease()

    init {
        require(sampleRate in 8000..192000)
        capacity = sampleRate / 10
        storage = ShortArray(capacity * 4)
        scratch = ShortArray(capacity)
        if (!detector.begin(token)) { close(); throw IllegalStateException() }
    }

    fun submit(input: ShortArray, count: Int, sampleRate: Int): Boolean = synchronized(queue) {
        if (token.cancelled) { open = false; lease.active = false; clearLocked() }
        if (!open) return false
        val time = now()
        if (sampleRate != this.sampleRate || count !in 1..input.size || count > capacity ||
            size == 4 || !clockValid(time) || (size > 0 && !fresh(time, times[head]))) {
            failLocked(); return false
        }
        lastClock = time
        val slot = (head + size) % 4
        input.copyInto(storage, slot * capacity, 0, count)
        counts[slot] = count; times[slot] = time; size++
        true
    }

    fun drain(): WakeDrain = synchronized(consumer) {
        try {
            val events = mutableListOf<WakeCaptureActivation>()
            repeat(4) {
                var terminal: WakeDrain? = null
                val count = synchronized(queue) {
                    if (token.cancelled) { open = false; lease.active = false; clearLocked() }
                    when {
                        failed -> { terminal = if (reported) WakeDrain.Inactive else WakeDrain.Failed; reported = true; 0 }
                        !open -> { terminal = WakeDrain.Inactive; 0 }
                        size == 0 -> 0
                        else -> {
                            val time = now()
                            if (!clockValid(time) || !fresh(time, times[head])) {
                                failLocked(); reported = true; terminal = WakeDrain.Failed; 0
                            } else {
                                lastClock = time
                                val n = counts[head]; val offset = head * capacity
                                storage.copyInto(scratch, 0, offset, offset + n)
                                storage.fill(0, offset, offset + capacity)
                                counts[head] = 0; times[head] = 0; head = (head + 1) % 4; size--
                                n
                            }
                        }
                    }
                }
                terminal?.let { detector.close(); return it }
                if (count == 0) return WakeDrain.Events(events)
                val event = detector.processPCM16(token, scratch, count, sampleRate)
                scratch.fill(0)
                if (!detector.isActive(token)) {
                    if (token.cancelled) { close(); return WakeDrain.Inactive }
                    val result = synchronized(queue) {
                        if (!open && !failed) WakeDrain.Inactive
                        else if (failed && reported) WakeDrain.Inactive
                        else { failLocked(); reported = true; WakeDrain.Failed }
                    }
                    detector.close(); return result
                }
                if (event != null && lease.active) events.add(WakeCaptureActivation(event, lease))
            }
            WakeDrain.Events(events)
        } finally { scratch.fill(0) }
    }

    // Subtraction overflow represents an invalid elapsed interval, never a fresh frame.
    private fun fresh(time: Long, received: Long) = time >= received && time - received in 0 until 250_000_000L
    private fun clockValid(time: Long) = lastClock?.let { time >= it } ?: true
    private fun clearLocked() {
        storage.fill(0); counts.fill(0); times.fill(0); head = 0; size = 0; lastClock = null
    }
    private fun failLocked() { open = false; failed = true; lease.active = false; clearLocked() }
    fun close() {
        // Revoke queued metadata before waiting for a synchronous borrowed decode.
        synchronized(queue) { open = false; failed = false; lease.active = false; clearLocked() }
        synchronized(consumer) { scratch.fill(0); detector.close() }
    }
}
