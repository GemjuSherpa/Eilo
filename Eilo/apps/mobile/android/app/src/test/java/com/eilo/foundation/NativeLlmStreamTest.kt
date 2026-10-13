package com.eilo.foundation

import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import org.junit.Assert.*
import org.junit.Test

class NativeLlmStreamTest {
    private class Api : NativeLlmApi {
        var creates = 0; var loads = 0; var begins = 0; var nexts = 0
        var cancels = 0; var destroys = 0
        var onCreate: () -> Long = { 7L }
        var onLoad: () -> Int = { 0 }
        var onBegin: () -> Int = { 0 }
        var onNext: (ByteArray, IntArray) -> Int = { out, n -> out[0] = 65; n[0] = 1; 1 }
        var onCancel: () -> Unit = {}
        override fun create(): Long { creates++; return onCreate() }
        override fun load(handle: Long, descriptor: Int, threads: Int): Int { loads++; return onLoad() }
        override fun begin(handle: Long, prompt: ByteArray, count: Int, outputLimit: Int): Int {
            begins++; assertEquals(prompt.size, count); return onBegin()
        }
        override fun next(handle: Long, output: ByteArray, count: IntArray): Int {
            nexts++; return onNext(output, count)
        }
        override fun cancel(handle: Long) { cancels++; onCancel() }
        override fun destroy(handle: Long) { destroys++ }
    }
    private fun failure(reason: LlmFailureReason = LlmFailureReason.UNAVAILABLE, action: () -> Unit) {
        try { action(); fail("expected bounded failure") }
        catch (error: LlmFailure) {
            assertEquals(reason, error.reason); assertEquals("LLM unavailable", error.message)
            assertNull(error.cause)
        }
    }
    private fun generating(api: Api, allowed: () -> Boolean = { true }): NativeLlmStream =
        NativeLlmStream(allowed, api).also { it.load(3); it.begin(byteArrayOf(65), 8) }

    @Test fun defaultApiDoesNotCreateAnAvailableStream() = failure { NativeLlmStream({ true }) }
    @Test fun invalidLeaseDoesNotAllocate() {
        val api = Api(); failure { NativeLlmStream({ false }, api) }; assertEquals(0, api.creates)
    }
    @Test fun leaseRevokedDuringCreateReleasesExactlyOnce() {
        var allowed = true; val api = Api().apply { onCreate = { allowed = false; 7L } }
        failure { NativeLlmStream({ allowed }, api) }; assertEquals(1, api.destroys)
    }
    @Test fun failedCreateStripsBackendContent() {
        val api = Api().apply { onCreate = { throw IllegalStateException("synthetic backend detail") } }
        failure { NativeLlmStream({ true }, api) }; assertEquals(0, api.destroys)
    }
    @Test fun invalidDescriptorAndThreadLimitsDoNotReachNative() {
        for ((fd, threads) in listOf(-1 to 2, 3 to 0, 3 to 9)) {
            val api = Api(); val stream = NativeLlmStream({ true }, api)
            failure { stream.load(fd, threads) }; assertEquals(0, api.loads); assertEquals(1, api.destroys)
        }
    }
    @Test fun beginRequiresLoadedStateAndRejectsUnboundedOrNulPrompt() {
        val first = Api(); failure { NativeLlmStream({ true }, first).begin(byteArrayOf(65), 8) }
        assertEquals(0, first.begins)
        for (prompt in listOf(byteArrayOf(), byteArrayOf(65, 0), ByteArray(16385) { 65 })) {
            val api = Api(); val stream = NativeLlmStream({ true }, api); stream.load(3)
            failure { stream.begin(prompt, 8) }; assertEquals(0, api.begins); assertEquals(1, api.destroys)
        }
    }
    @Test fun outputLimitsAreBoundedBeforeNative() {
        for (limit in listOf(0, 257)) {
            val api = Api(); val stream = NativeLlmStream({ true }, api); stream.load(3)
            failure { stream.begin(byteArrayOf(65), limit) }; assertEquals(0, api.begins)
        }
    }
    @Test fun nativeCancellationHasTypedContentFreeFailure() {
        val api = Api().apply { onLoad = { -2 } }; val stream = NativeLlmStream({ true }, api)
        failure(LlmFailureReason.CANCELLED) { stream.load(3) }; assertEquals(1, api.destroys)
    }
    @Test fun leaseRevokedDuringEveryNativeOperationRejectsOutput() {
        for (phase in listOf("load", "begin", "next")) {
            var allowed = true; val api = Api(); val stream = NativeLlmStream({ allowed }, api)
            if (phase == "load") api.onLoad = { allowed = false; 0 }
            if (phase == "begin") api.onBegin = { allowed = false; 0 }
            if (phase == "next") api.onNext = { out, n -> allowed = false; out[0] = 65; n[0] = 1; 1 }
            failure {
                stream.load(3); stream.begin(byteArrayOf(65), 8)
                stream.withNextPiece { _, _ -> fail("revoked piece released") }
            }
            assertEquals(1, api.destroys)
        }
    }
    @Test fun malformedNativeStatusesAndLengthsFailClosed() {
        for ((status, length) in listOf(1 to 0, 1 to 1025, 0 to 1, -3 to 1, 2 to 1)) {
            val api = Api().apply { onNext = { out, n -> out[0] = 65; n[0] = length; status } }
            val stream = generating(api)
            failure { stream.withNextPiece { _, _ -> fail("invalid piece released") } }
            assertEquals(1, api.destroys)
        }
    }
    @Test fun rawUtf8FragmentsAreBorrowedAndClearedAfterConsumption() {
        val fragments = listOf(byteArrayOf(0xe2.toByte()), byteArrayOf(0x82.toByte(), 0xac.toByte()))
        var index = 0; var previous: ByteArray? = null; val joined = ArrayList<Byte>()
        val api = Api().apply { onNext = { out, n ->
            assertTrue(out.all { it == 0.toByte() }); assertEquals(0, n[0])
            fragments[index++].copyInto(out); n[0] = fragments[index - 1].size; 1
        } }
        val stream = generating(api)
        repeat(2) {
            assertTrue(stream.withNextPiece { out, n ->
                if (previous != null) assertSame(previous, out)
                previous = out; joined.addAll(out.take(n))
            }); assertTrue(previous!!.all { it == 0.toByte() })
        }
        assertEquals("€", joined.toByteArray().toString(Charsets.UTF_8)); stream.close()
    }
    @Test fun completionAndRepeatedCloseReleaseExactlyOnce() {
        val api = Api().apply { onNext = { _, n -> n[0] = 0; 0 } }; val stream = generating(api)
        assertFalse(stream.withNextPiece { _, _ -> fail("end released token") })
        stream.close(); stream.close(); assertEquals(1, api.destroys)
    }
    @Test fun consumerExceptionStillClearsBorrowedScratch() {
        var borrowed: ByteArray? = null; val stream = generating(Api())
        try { stream.withNextPiece { out, _ -> borrowed = out; throw IllegalArgumentException() }; fail() }
        catch (_: IllegalArgumentException) { assertTrue(borrowed!!.all { it == 0.toByte() }) }
        finally { stream.close() }
    }
    @Test fun nativeNextFailureClosesAndStripsItsCause() {
        val api = Api().apply { onNext = { _, _ -> throw IllegalStateException("synthetic backend detail") } }
        failure { generating(api).withNextPiece { _, _ -> fail("unexpected piece") } }
        assertEquals(1, api.destroys)
    }
    @Test fun cancellationDoesNotWaitForDecodeOrDestroyItsHandle() {
        val entered = CountDownLatch(1); val release = CountDownLatch(1)
        val error = AtomicReference<Throwable?>(); val api = Api().apply { onNext = { out, n ->
            entered.countDown(); check(release.await(5, TimeUnit.SECONDS)); out[0] = 65; n[0] = 1; 1
        } }
        val stream = generating(api)
        val worker = Thread {
            try { stream.withNextPiece { _, _ -> fail("cancelled piece released") } }
            catch (failure: Throwable) { error.set(failure) }
        }
        worker.start()
        try {
            assertTrue(entered.await(5, TimeUnit.SECONDS)); assertTrue(stream.requestCancellation())
            assertEquals(0, api.destroys)
        } finally { release.countDown(); worker.join(5000) }
        assertFalse(worker.isAlive); assertEquals(LlmFailureReason.CANCELLED, (error.get() as LlmFailure).reason)
        assertEquals(1, api.destroys)
    }
    @Test fun failedCancelSignalIsReportedAndLocallyRejectsForever() {
        val api = Api().apply { onCancel = { throw UnsatisfiedLinkError("synthetic detail") } }
        val stream = generating(api); assertFalse(stream.requestCancellation())
        failure { stream.withNextPiece { _, _ -> fail("cancelled piece released") } }
        assertEquals(0, api.nexts); assertEquals(1, api.destroys)
    }
    @Test fun leaseExceptionsFailClosed() {
        val api = Api(); failure { NativeLlmStream({ throw IllegalStateException() }, api) }
        assertEquals(0, api.creates)
    }
}

class NativeLlmRuntimeTest {
    @Test fun defaultAndReleaseEvaluationNeverAttemptLoading() {
        for ((evaluation, debug) in listOf(false to true, true to false, false to false)) {
            val runtime = NativeLlmRuntime(evaluation, debug, { fail("loading forbidden") }, { fail(); false })
            assertNull(runtime.load()); assertNull(runtime.load())
        }
    }
    @Test fun explicitDebugLoadsOnlyFixedNameOnce() {
        var calls = 0; var probes = 0
        val runtime = NativeLlmRuntime(true, true, { name -> assertEquals("eilo_llm_jni", name); calls++ },
            { probes++; true }, UnavailableLlmApi)
        assertSame(UnavailableLlmApi, runtime.load()); assertSame(UnavailableLlmApi, runtime.load())
        assertEquals(1, calls); assertEquals(1, probes)
    }
    @Test fun loadFailureNeverRetriesOrProbes() {
        var calls = 0; val runtime = NativeLlmRuntime(true, true,
            { calls++; throw UnsatisfiedLinkError("synthetic detail") }, { fail("probe after failure"); true })
        assertNull(runtime.load()); assertNull(runtime.load()); assertEquals(1, calls)
    }
    @Test fun incompatibleOrFailedProbeNeverReturnsApi() {
        for (throws in listOf(false, true)) {
            var calls = 0
            val runtime = NativeLlmRuntime(true, true, { calls++ },
                { if (throws) throw IllegalStateException("synthetic detail") else false })
            assertNull(runtime.load()); assertNull(runtime.load()); assertEquals(1, calls)
        }
    }
}
