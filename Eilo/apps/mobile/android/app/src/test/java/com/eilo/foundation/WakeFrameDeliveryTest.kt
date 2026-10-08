package com.eilo.foundation

import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import kotlin.concurrent.thread

private class DeliveryEngine : WakeKeywordStream {
    var accepted = 0
    var closed = 0
    var result = "HEY EILO"
    var borrow: FloatArray? = null
    var observed = emptyList<Float>()
    var onAccept: () -> Unit = {}
    override fun accept(samples: FloatArray, count: Int, sampleRate: Int) {
        accepted++; borrow = samples; observed = samples.take(count); onAccept()
    }
    override fun ready() = false
    override fun decode() { error("unexpected") }
    override fun keyword() = result
    override fun reset() { result = "" }
    override fun close() { closed++ }
}

class WakeFrameDeliveryTest {
    private val config = WakeConfiguration("HEY EILO", .125f, 1.5f)
    private val pcm = shortArrayOf(-32768, 0, 32767)
    private fun delivery(engine: DeliveryEngine, token: GenerationToken, now: () -> Long = { 0L }) =
        WakeFrameDelivery(16000, WakeDetector(config, verified = { true }, open = { engine }), token, now)
    private fun assertErased(d: WakeFrameDelivery) {
        for (name in listOf("storage", "scratch")) {
            val field = WakeFrameDelivery::class.java.getDeclaredField(name); field.isAccessible = true
            assertTrue(name, (field.get(d) as ShortArray).all { it == 0.toShort() })
        }
    }
    private fun event(d: WakeFrameDelivery) = (d.drain() as WakeDrain.Events).values.single()

    @Test fun submitCopiesOnlyPrefixAndWorkerReturnsOnlyMetadata() {
        val c = testController(); c.dispatch(ControllerEvent.START)
        val e = DeliveryEngine(); val d = delivery(e, c.token()!!)
        val input = shortArrayOf(-32768, 0, 32767, 123)
        assertTrue(d.submit(input, 3, 16000)); assertEquals(0, e.accepted)
        input.fill(0)
        val result = event(d)
        assertEquals(listOf(-1f, 0f, 32767f / 32768f), e.observed)
        assertTrue(e.borrow!!.all { it == 0f }); assertEquals(ControllerState.STANDBY, c.state())
        assertTrue(result.apply(c)); assertFalse(result.apply(c)); d.close(); d.close()
        assertEquals(1, e.closed); assertErased(d)
    }

    @Test fun overflowRevokesPreviouslyReturnedActivationAndReportsOnce() {
        val c = testController(); c.dispatch(ControllerEvent.START)
        val e = DeliveryEngine(); val d = delivery(e, c.token()!!); d.submit(pcm, 3, 16000)
        val result = event(d)
        repeat(4) { assertTrue(d.submit(pcm, 3, 16000)) }
        assertFalse(d.submit(pcm, 3, 16000)); assertFalse(result.apply(c))
        assertSame(WakeDrain.Failed, d.drain()); assertSame(WakeDrain.Inactive, d.drain())
        assertEquals(1, e.accepted); assertEquals(1, e.closed); assertErased(d); assertErased(d)
    }

    @Test fun invalidBoundsAndRouteRateCloseWithoutDecoding() {
        for (input in listOf(Triple(pcm, 0, 16000), Triple(pcm, 4, 16000),
            Triple(ShortArray(1601), 1601, 16000), Triple(pcm, 3, 48000))) {
            val c = testController(); c.dispatch(ControllerEvent.START)
            val e = DeliveryEngine(); val d = delivery(e, c.token()!!)
            assertFalse(d.submit(input.first, input.second, input.third))
            assertSame(WakeDrain.Failed, d.drain()); assertEquals(0, e.accepted); assertEquals(1, e.closed)
        }
    }

    @Test fun staleAtBoundaryAndBackwardsClockFailClosedOnSubmitOrDrain() {
        for (atSubmit in listOf(false, true)) for (time in listOf(250_000_000L, -1L, Long.MAX_VALUE)) {
            var now = 0L
            val c = testController(); c.dispatch(ControllerEvent.START)
            val e = DeliveryEngine(); val d = delivery(e, c.token()!!) { now }
            assertTrue(d.submit(pcm, 3, 16000)); now = time
            if (atSubmit) assertFalse(d.submit(pcm, 3, 16000))
            assertSame(WakeDrain.Failed, d.drain()); assertEquals(0, e.accepted)
        }
    }

    @Test fun freshFramesDrainWithBoundedBatchAndNoWakeRemainsStandby() {
        var now = 0L
        val c = testController(); c.dispatch(ControllerEvent.START)
        val e = DeliveryEngine(); e.result = ""; val d = delivery(e, c.token()!!) { now }
        repeat(4) { assertTrue(d.submit(pcm, 3, 16000)) }; now = 249_999_999L
        assertTrue((d.drain() as WakeDrain.Events).values.isEmpty()); assertEquals(4, e.accepted)
        assertTrue((d.drain() as WakeDrain.Events).values.isEmpty())
        assertEquals(ControllerState.STANDBY, c.state()); d.close()
    }

    @Test fun cancellationAndVerificationRevocationEraseWithoutActivation() {
        for (cancel in listOf(false, true)) {
            val c = testController(); c.dispatch(ControllerEvent.START); val token = c.token()!!
            val e = DeliveryEngine(); var verified = true
            val d = WakeFrameDelivery(16000, WakeDetector(config, verified = { verified }, open = { e }), token)
            d.submit(pcm, 3, 16000)
            if (cancel) c.stop() else verified = false
            assertSame(if (cancel) WakeDrain.Inactive else WakeDrain.Failed, d.drain())
            assertEquals(0, e.accepted); assertEquals(1, e.closed)
        }
    }

    @Test fun closeRevokesMetadataBeforeWaitingForBorrowedDecodeAndDoesNotBlockSubmit() {
        val c = testController(); c.dispatch(ControllerEvent.START)
        val e = DeliveryEngine(); val d = delivery(e, c.token()!!)
        d.submit(pcm, 3, 16000); val pending = event(d)
        val entered = CountDownLatch(1); val release = CountDownLatch(1); val completed = CountDownLatch(1)
        val error = AtomicReference<Throwable?>()
        e.onAccept = { entered.countDown(); check(release.await(5, TimeUnit.SECONDS)) }
        d.submit(pcm, 3, 16000)
        val worker = thread { try { d.drain() } catch (t: Throwable) { error.set(t) } }
        assertTrue(entered.await(5, TimeUnit.SECONDS))
        // Decode does not hold the queue monitor.
        assertTrue(d.submit(pcm, 3, 16000))
        val closer = thread { try { d.close() } finally { completed.countDown() } }
        try {
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
            while (closer.state != Thread.State.BLOCKED && System.nanoTime() < deadline) Thread.yield()
            assertEquals(Thread.State.BLOCKED, closer.state)
            assertFalse(d.submit(pcm, 3, 16000))
            assertFalse(pending.apply(c)); assertFalse(completed.await(20, TimeUnit.MILLISECONDS))
        } finally { release.countDown(); worker.join(5000); closer.join(5000) }
        assertFalse(worker.isAlive); assertFalse(closer.isAlive); assertNull(error.get())
        assertTrue(e.borrow!!.all { it == 0f }); assertEquals(1, e.closed)
        assertSame(WakeDrain.Inactive, d.drain()); assertErased(d)
    }

    @Test fun missingPackAndInvalidRateCannotCreateDelivery() {
        val c = testController(); c.dispatch(ControllerEvent.START); val token = c.token()!!
        assertThrows(IllegalStateException::class.java) { WakeFrameDelivery(16000, WakeDetector(config), token) }
        assertThrows(IllegalArgumentException::class.java) { WakeFrameDelivery(7999, WakeDetector(config), token) }
    }
}
