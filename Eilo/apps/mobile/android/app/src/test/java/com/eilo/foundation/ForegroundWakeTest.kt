package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.Executors
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import kotlin.concurrent.thread

private class CaptureWakeEngine : WakeKeywordStream {
    val decoded = CountDownLatch(1)
    var onAccept: () -> Unit = {}
    var borrowed: FloatArray? = null
    var matched = true
    @Volatile var closed = 0
    override fun accept(samples: FloatArray, count: Int, sampleRate: Int) {
        assertEquals(16000, sampleRate); assertEquals(320, count)
        assertTrue(samples.take(count).all { it == 42f / 32768f })
        borrowed = samples; onAccept(); decoded.countDown()
    }
    override fun ready() = false
    override fun decode() { error("unexpected") }
    override fun keyword() = if (matched) "HEY EILO" else ""
    override fun reset() { matched = false }
    override fun close() { closed++ }
}

class ForegroundWakeTest {
    private val config = WakeConfiguration("HEY EILO", .125f, 1.5f)
    private fun delivery(e: CaptureWakeEngine, token: GenerationToken) = WakeFrameDelivery(16000,
        WakeDetector(config, verified = { true }, open = { e }), token)
    private fun await(check: () -> Boolean) {
        val limit = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
        while (!check() && System.nanoTime() < limit) Thread.sleep(1)
        assertTrue(check())
    }
    private class Device : CaptureDevice {
        val feed = AtomicBoolean(false)
        var borrowed: ShortArray? = null
        val closed = AtomicBoolean(false)
        override fun start() {}
        override fun read(samples: ShortArray): Int {
            borrowed = samples
            if (!feed.get()) return 0
            samples.fill(42); return 320
        }
        override fun close() { closed.set(true) }
    }
    @Test fun realCaptureLoopFeedsWorkerAndRejectsWrongControllerOrGeneration() {
        val executor = Executors.newSingleThreadExecutor(); val device = Device()
        val capture = ForegroundCapture(executor, {true}, {device}); val c = testController(effects = capture)
        val wrong = testController(); wrong.dispatch(ControllerEvent.START)
        try {
            c.dispatch(ControllerEvent.START); await { c.state() == ControllerState.STANDBY }
            val token = c.token()!!; val e = CaptureWakeEngine(); val d = delivery(e, token)
            val foreign = delivery(CaptureWakeEngine(), wrong.token()!!)
            assertFalse(capture.attachWakeDelivery(wrong, wrong.token()!!, foreign)); foreign.close()
            assertFalse(capture.attachWakeDelivery(c, wrong.token()!!, d))
            val wrongRate = WakeFrameDelivery(48000, WakeDetector(config, verified = {true}, open = {CaptureWakeEngine()}), token)
            assertFalse(capture.attachWakeDelivery(c, token, wrongRate)); wrongRate.close()
            assertTrue(capture.attachWakeDelivery(c, token, d)); assertFalse(capture.attachWakeDelivery(c, token, d))
            device.feed.set(true); assertTrue(e.decoded.await(5, TimeUnit.SECONDS))
            await { c.state() == ControllerState.CAPTURING }; await { e.closed == 1 }
            c.stop(); assertTrue(device.closed.get()); assertTrue(token.cancelled)
            assertFalse(capture.attachWakeDelivery(c, token, d))
            assertTrue(device.borrowed!!.all { it == 0.toShort() }); assertTrue(e.borrowed!!.all { it == 0f })
        } finally { c.stop(); wrong.stop(); executor.shutdownNow(); assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS)) }
    }
    @Test fun stopDuringDecodeWaitsWithoutControllerCaptureDeadlockAndCannotActivate() {
        val executor = Executors.newSingleThreadExecutor(); val device = Device()
        val capture = ForegroundCapture(executor, {true}, {device}); val c = testController(effects = capture)
        val entered = CountDownLatch(1); val release = CountDownLatch(1); val stopped = CountDownLatch(1)
        val error = AtomicReference<Throwable?>(); var stopper: Thread? = null
        val e = CaptureWakeEngine(); e.onAccept = { entered.countDown(); check(release.await(5, TimeUnit.SECONDS)) }
        try {
            c.dispatch(ControllerEvent.START); await { c.state() == ControllerState.STANDBY }; val token = c.token()!!
            assertTrue(capture.attachWakeDelivery(c, token, delivery(e, token))); device.feed.set(true)
            assertTrue(entered.await(5, TimeUnit.SECONDS))
            stopper = thread { try { c.stop() } catch (t: Throwable) { error.set(t) } finally { stopped.countDown() } }
            await { token.cancelled }; assertFalse(stopped.await(20, TimeUnit.MILLISECONDS))
            release.countDown(); assertTrue(stopped.await(5, TimeUnit.SECONDS)); stopper.join(5000)
            assertNull(error.get()); assertEquals(ControllerState.STOPPED, c.state())
            assertTrue(device.closed.get()); assertEquals(1, e.closed)
            assertTrue(device.borrowed!!.all { it == 0.toShort() }); assertTrue(e.borrowed!!.all { it == 0f })
        } finally { release.countDown(); stopper?.join(5000); c.stop(); executor.shutdownNow(); assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS)) }
    }
    @Test fun detachedGenerationCanReattachWithoutReopeningAndBackendFailureStopsCapture() {
        val executor = Executors.newSingleThreadExecutor(); val device = Device()
        val capture = ForegroundCapture(executor, {true}, {device}); val c = testController(effects = capture)
        val first = CaptureWakeEngine(); val failed = CaptureWakeEngine(); failed.onAccept = { error("synthetic") }
        try {
            c.dispatch(ControllerEvent.START); await { c.state() == ControllerState.STANDBY }; val token = c.token()!!
            assertTrue(capture.attachWakeDelivery(c, token, delivery(first, token)))
            capture.clearVolatileContext(); assertEquals(1, first.closed); assertFalse(device.closed.get())
            assertTrue(capture.attachWakeDelivery(c, token, delivery(failed, token))); device.feed.set(true)
            await { c.state() == ControllerState.ERROR }
            assertTrue(device.closed.get()); assertTrue(token.cancelled); assertEquals(1, failed.closed)
            assertTrue(device.borrowed!!.all { it == 0.toShort() })
        } finally { c.stop(); executor.shutdownNow(); assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS)) }
    }
    @Test fun detachedFailingBorrowCannotStopReplacementBinding() {
        val executor = Executors.newSingleThreadExecutor(); val device = Device()
        val capture = ForegroundCapture(executor, {true}, {device}); val c = testController(effects = capture)
        val entered = CountDownLatch(1); val release = CountDownLatch(1); var clearing: Thread? = null
        val old = CaptureWakeEngine(); old.onAccept = {
            entered.countDown(); check(release.await(5, TimeUnit.SECONDS)); error("synthetic old failure")
        }
        val fresh = CaptureWakeEngine(); fresh.matched = false
        try {
            c.dispatch(ControllerEvent.START); await { c.state() == ControllerState.STANDBY }; val token = c.token()!!
            assertTrue(capture.attachWakeDelivery(c, token, delivery(old, token))); device.feed.set(true)
            assertTrue(entered.await(5, TimeUnit.SECONDS)); device.feed.set(false)
            clearing = thread { capture.clearVolatileContext() }
            val replacement = delivery(fresh, token)
            var attached = false
            await { if (!attached) attached = capture.attachWakeDelivery(c, token, replacement); attached }
            release.countDown(); clearing.join(5000); assertFalse(clearing.isAlive)
            // The old failure reaches the controller only after its binding lease was revoked.
            device.feed.set(true); assertTrue(fresh.decoded.await(5, TimeUnit.SECONDS))
            assertEquals(ControllerState.STANDBY, c.state()); assertFalse(token.cancelled)
            assertEquals(1, old.closed); assertEquals(0, fresh.closed); c.stop(); assertEquals(1, fresh.closed)
        } finally { release.countDown(); clearing?.join(5000); c.stop(); executor.shutdownNow(); assertTrue(executor.awaitTermination(5, TimeUnit.SECONDS)) }
    }

}
