package com.eilo.foundation

import java.io.File
import java.nio.file.Files
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executor
import java.util.concurrent.RejectedExecutionException
import java.util.concurrent.TimeUnit
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class LlmControllerJobTest {
    private class Fixture : AutoCloseable {
        val root = Files.createTempDirectory("eilo-llm-job").toFile()
        val source = File(root, "source").apply { writeBytes(byteArrayOf(1, 2, 3, 4)) }
        val hash = MessageDigest.getInstance("SHA-256").digest(source.readBytes()).joinToString("") { "%02x".format(it) }
        val evidence = "c".repeat(64); val runtime = "a".repeat(40)
        val key = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()
        val trust = mapOf("test-key" to key.public.encoded)
        val store = PackStore(File(root, "store"), trust, runtime, setOf(evidence))
        val selection = LlmPackSelection("test-pack", runtime, LlmArtifactPin("model", hash, 4, evidence))
        val pack: VerifiedPack
        var opens = 0; var closes = 0
        var onOpen: () -> Unit = {}; var onClose: () -> Unit = {}
        init {
            val artifact = JSONObject().put("id", "model").put("filename", "model.gguf").put("role", "llm")
                .put("url", "https://models.example.test/model.gguf").put("sha256", hash).put("bytes", 4)
                .put("license", "Apache-2.0").put("licenseEvidence", evidence)
            val bytes = JSONObject().put("schema", 1).put("packId", "test-pack").put("revision", 1)
                .put("runtimeRevision", runtime).put("minAndroid", 35).put("minIos", 18)
                .put("artifacts", JSONArray().put(artifact)).toString().replace("\\/", "/").toByteArray()
            val signer = Signature.getInstance("SHA256withECDSA"); signer.initSign(key.private); signer.update(bytes)
            pack = VerifiedPack.verify(bytes, signer.sign(), "test-key", "ES256", trust, runtime)
            activate()
        }
        fun activate() { store.activate(pack, listOf(VerifiedArtifact.verify(pack, 0, source)), PackCancellation()) }
        fun open(file: File, pin: LlmArtifactPin): LlmVerifiedDescriptor {
            assertEquals("model.gguf", file.name); assertEquals(hash, pin.sha256)
            opens++; onOpen(); return LlmVerifiedDescriptor(31) { closes++; onClose() }
        }
        override fun close() { root.deleteRecursively() }
    }
    private class Queue : Executor {
        val tasks = ArrayList<Runnable>()
        override fun execute(task: Runnable) { tasks.add(task) }
        fun launch(): Thread = Thread(tasks.removeAt(0), "eilo-model-test").apply { start() }
        fun drain() { val t = launch(); t.join(5000); assertFalse("worker did not join", t.isAlive) }
    }
    private open class Api : NativeLlmApi {
        var creates = 0; var loads = 0; var begins = 0; var nexts = 0; var cancels = 0; var destroys = 0
        var borrowedPrompt: ByteArray? = null; var borrowedPiece: ByteArray? = null
        val workerThreads = ArrayList<Thread>()
        var onLoad: () -> Int = { 0 }; var onBegin: () -> Int = { 0 }
        var onNext: () -> Unit = {}; var onCancel: () -> Unit = {}; var onDestroy: () -> Unit = {}
        override fun create(): Long { creates++; workerThreads.add(Thread.currentThread()); return 7L }
        override fun load(handle: Long, descriptor: Int, threads: Int): Int {
            loads++; workerThreads.add(Thread.currentThread()); assertEquals(31, descriptor); return onLoad()
        }
        override fun begin(handle: Long, prompt: ByteArray, count: Int, outputLimit: Int): Int {
            begins++; workerThreads.add(Thread.currentThread()); borrowedPrompt = prompt; assertEquals(65, prompt[0].toInt()); return onBegin()
        }
        override fun next(handle: Long, output: ByteArray, count: IntArray): Int {
            nexts++; workerThreads.add(Thread.currentThread()); borrowedPiece = output
            if (nexts == 1) { output[0] = 66; count[0] = 1; onNext(); return 1 }
            count[0] = 0; return 0
        }
        override fun cancel(handle: Long) { cancels++; onCancel() }
        override fun destroy(handle: Long) { destroys++; workerThreads.add(Thread.currentThread()); onDestroy() }
    }
    private class Effects : ControllerEffects {
        override fun startCapture() = true
        override fun playClause(clause: String) { fail("raw token must never become speech") }
        override fun cancelWork() {}
        override fun releaseCapture() {}
        override fun clearVolatileContext() {}
    }
    private fun controller(permission: MicrophonePermissionAdapter = object : MicrophonePermissionAdapter {
        override fun status() = MicrophonePermission.GRANTED
        override fun request(completion: (MicrophonePermission) -> Unit) { completion(status()) }
    }): NativeController = NativeController(effects = Effects(), permission = permission,
        models = ModelReadinessAdapter { ModelStatus.READY }).apply {
        assertTrue(dispatch(ControllerEvent.START))
        assertTrue(dispatch(ControllerEvent.SPEECH_DETECTED, token = token()))
        assertTrue(dispatch(ControllerEvent.ENDPOINT, token = token()))
    }
    private fun submit(f: Fixture, c: NativeController, q: Executor, api: NativeLlmApi = Api(),
        prompt: ByteArray = byteArrayOf(65), token: GenerationToken = c.token()!!,
        limit: Int = 8, consume: (ByteArray, Int) -> Unit = { _, _ -> },
    ) = LlmControllerJob.submit(c, token, q, f.store, f.selection, prompt, limit, api = api,
        openDescriptor = f::open, workerThreadAllowed = { true }, consume = consume)
    private fun result(job: LlmControllerJob, expected: LlmJobResult) {
        assertEquals(expected, job.awaitCompletion(5, TimeUnit.SECONDS))
    }

    @Test fun signedJobRunsOffCallingThreadWithBorrowedBytesAndNoSpeech() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api(); val prompt = byteArrayOf(65)
            var borrowed: ByteArray? = null
            val job = submit(f, c, q, api, prompt) { out, n ->
                assertEquals(1, n); assertEquals(66, out[0].toInt()); borrowed = out
                assertNull(jobJoinFromController(c))
            }!!
            assertEquals(0, api.creates); q.drain(); result(job, LlmJobResult.COMPLETED)
            assertTrue(api.workerThreads.all { it !== Thread.currentThread() })
            assertTrue(prompt.all { it == 0.toByte() }); assertTrue(borrowed!!.all { it == 0.toByte() })
            assertSame(prompt, api.borrowedPrompt); assertEquals(1, api.destroys); assertEquals(1, f.closes)
            assertEquals(ControllerState.THINKING, c.state())
            assertFalse(c.snapshot().values.any { it is ByteArray })
        }
    }
    // Await refuses controller-monitor callers, even with zero timeout.
    private var joinTarget: LlmControllerJob? = null
    private fun jobJoinFromController(c: NativeController): LlmJobResult? = synchronized(c) {
        joinTarget?.awaitCompletion(0, TimeUnit.SECONDS)
    }
    @Test fun queuedStopErasesPromptAndNeverOpensOrCreates() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api(); val prompt = byteArrayOf(65)
            val job = submit(f, c, q, api, prompt)!!; c.stop()
            assertEquals(0, prompt[0].toInt()); q.drain(); result(job, LlmJobResult.CANCELLED)
            assertEquals(0, f.opens); assertEquals(0, api.creates); assertEquals(ControllerState.STOPPED, c.state())
        }
    }
    @Test fun staleForeignDuplicateAndWrongStateTicketsAreRejectedAndCleared() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val old = c.token()!!; val other = controller().token()!!
            for (token in listOf(other)) {
                val prompt = byteArrayOf(65); assertNull(submit(f, c, q, prompt = prompt, token = token)); assertEquals(0, prompt[0].toInt())
            }
            val job = submit(f, c, q)!!; val duplicate = byteArrayOf(65)
            assertNull(submit(f, c, q, prompt = duplicate)); assertEquals(0, duplicate[0].toInt())
            c.cancelGeneration(); assertNull(submit(f, c, q, token = old)); q.drain(); result(job, LlmJobResult.CANCELLED)
        }
    }
    @Test fun everyPrivacyTransitionRevokesQueuedWorkWithoutCreatingNativeHandle() {
        Fixture().use { f ->
            for (change in PrivacyChange.entries) {
                val c = controller(); val q = Queue(); val api = Api(); val prompt = byteArrayOf(65)
                val job = submit(f, c, q, api, prompt)!!; c.privacyTransition(change)
                assertEquals(0, prompt[0].toInt()); q.drain(); result(job, LlmJobResult.CANCELLED); assertEquals(0, api.creates)
            }
        }
    }
    @Test fun endpointStateRequiredAndInvalidBoundsNeverSchedule() {
        Fixture().use { f ->
            val c = controller(); val q = Queue();
            for (prompt in listOf(byteArrayOf(), byteArrayOf(65, 0), ByteArray(16385) { 65 })) {
                assertNull(submit(f, c, q, prompt = prompt)); assertTrue(prompt.all { it == 0.toByte() })
            }
            for (limit in listOf(0, 257)) assertNull(submit(f, c, q, limit = limit))
            val beforeEndpoint = controller().apply { cancelGeneration() }
            assertNull(submit(f, beforeEndpoint, q)); assertTrue(q.tasks.isEmpty())
        }
    }
    @Test fun inlineAndRejectedExecutorsFailWithoutModelIoAndReleaseRegistration() {
        Fixture().use { f ->
            for (executor in listOf(Executor { it.run() }, Executor { throw RejectedExecutionException("synthetic detail") })) {
                val c = controller(); val prompt = byteArrayOf(65)
                val job = submit(f, c, executor, prompt = prompt)!!; result(job, LlmJobResult.UNAVAILABLE)
                assertEquals(0, prompt[0].toInt()); assertEquals(0, f.opens); assertEquals(ControllerState.ERROR, c.state())
                assertEquals(SafeError.UNAVAILABLE, c.error())
            }
        }
    }
    @Test fun missingDefaultRuntimeMapsToSafeErrorAndClosesDescriptor() {
        Fixture().use { f ->
            val c = controller(); val q = Queue()
            val job = submit(f, c, q, UnavailableLlmApi)!!; q.drain(); result(job, LlmJobResult.UNAVAILABLE)
            assertEquals(ControllerState.ERROR, c.state()); assertEquals(SafeError.UNAVAILABLE, c.error()); assertEquals(1, f.closes)
        }
    }
    @Test fun stopDuringDescriptorOpenRejectsBeforeCreateAndCleansUp() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api(); f.onOpen = { c.stop() }
            val job = submit(f, c, q, api)!!; q.drain(); result(job, LlmJobResult.CANCELLED)
            assertEquals(0, api.creates); assertEquals(1, f.closes)
        }
    }
    @Test fun stopDuringLoadAndPrefillSignalsWithoutJoiningOrDestroyingActiveWorker() {
        for (phase in listOf("load", "begin")) Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api(); val entered = CountDownLatch(1); val release = CountDownLatch(1)
            val blocking = { entered.countDown(); check(release.await(5, TimeUnit.SECONDS)); 0 }
            if (phase == "load") api.onLoad = blocking else api.onBegin = blocking
            val prompt = byteArrayOf(65); val job = submit(f, c, q, api, prompt)!!; val worker = q.launch()
            try {
                assertTrue(entered.await(5, TimeUnit.SECONDS)); assertTrue(c.stop()); assertTrue(api.cancels > 0)
                assertEquals(0, api.destroys); assertNull(job.awaitCompletion(0, TimeUnit.SECONDS))
                if (phase == "load") assertEquals(0, prompt[0].toInt()) else assertEquals(65, prompt[0].toInt())
            } finally { release.countDown(); worker.join(5000) }
            assertFalse(worker.isAlive); result(job, LlmJobResult.CANCELLED); assertEquals(1, api.destroys)
            assertEquals(0, prompt[0].toInt()); assertEquals(1, f.closes)
        }
    }
    @Test fun stopDuringDecodeRejectsPieceAndOldCompletionCannotChangeRestartedTurn() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api(); val entered = CountDownLatch(1); val release = CountDownLatch(1)
            api.onNext = { entered.countDown(); check(release.await(5, TimeUnit.SECONDS)) }
            val job = submit(f, c, q, api, consume = { _, _ -> fail("late piece released") })!!; val worker = q.launch()
            try {
                assertTrue(entered.await(5, TimeUnit.SECONDS)); c.stop(); assertEquals(0, api.destroys)
                assertTrue(c.dispatch(ControllerEvent.START)); assertTrue(c.dispatch(ControllerEvent.SPEECH_DETECTED, token = c.token()))
                assertTrue(c.dispatch(ControllerEvent.ENDPOINT, token = c.token()))
            } finally { release.countDown(); worker.join(5000) }
            assertFalse(worker.isAlive); result(job, LlmJobResult.CANCELLED)
            assertEquals(ControllerState.THINKING, c.state()); assertEquals(1, api.destroys)
            assertTrue(api.borrowedPiece!!.all { it == 0.toByte() })
            val newJob = submit(f, c, q)!!; q.drain(); result(newJob, LlmJobResult.COMPLETED)
        }
    }
    @Test fun permissionRevocationCancelsDecodeAndNeverReleasesRawPiece() {
        Fixture().use { f ->
            var granted = true
            val permission = object : MicrophonePermissionAdapter {
                override fun status() = if (granted) MicrophonePermission.GRANTED else MicrophonePermission.DENIED
                override fun request(completion: (MicrophonePermission) -> Unit) { completion(status()) }
            }
            val c = controller(permission); val q = Queue(); val api = Api().apply { onNext = { granted = false; c.permissionChanged() } }
            val job = submit(f, c, q, api, consume = { _, _ -> fail("revoked permission piece") })!!
            q.drain(); result(job, LlmJobResult.CANCELLED); assertEquals(ControllerState.STOPPED, c.state())
        }
    }
    @Test fun changedPackRejectsAlreadyDecodedPieceAndMapsUnavailable() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api().apply { onNext = { f.activate() } }
            val job = submit(f, c, q, api, consume = { _, _ -> fail("revoked pack piece") })!!
            q.drain(); result(job, LlmJobResult.UNAVAILABLE); assertEquals(ControllerState.ERROR, c.state())
            assertEquals(1, api.destroys); assertTrue(api.borrowedPiece!!.all { it == 0.toByte() })
        }
    }
    @Test fun nativeAndConsumerFailuresNeverExportBackendDetailsOrRetainScratch() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api().apply { onLoad = { throw IllegalStateException("synthetic detail") } }
            val job = submit(f, c, q, api)!!; q.drain(); result(job, LlmJobResult.UNAVAILABLE)
            assertEquals("unavailable", c.snapshot()["errorCode"]); assertEquals(1, api.destroys)
            val consumerController = controller(); val other = Api()
            val failing = submit(f, consumerController, q, other, consume = { _, _ -> throw IllegalStateException("synthetic detail") })!!
            q.drain(); result(failing, LlmJobResult.CANCELLED); assertTrue(other.borrowedPiece!!.all { it == 0.toByte() })
        }
    }
    @Test fun explicitCancellationAndFailedSignalRejectForeverAndAwaitWorkerCleanup() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api(); val entered = CountDownLatch(1); val release = CountDownLatch(1)
            api.onNext = { entered.countDown(); check(release.await(5, TimeUnit.SECONDS)) }
            val job = submit(f, c, q, api, consume = { _, _ -> fail("cancelled piece") })!!; val worker = q.launch()
            try {
                assertTrue(entered.await(5, TimeUnit.SECONDS)); api.onCancel = { throw IllegalStateException("synthetic detail") }
                assertFalse(job.requestCancellation()); assertEquals(0, api.destroys)
            } finally { api.onCancel = {}; release.countDown(); worker.join(5000) }
            assertFalse(worker.isAlive); result(job, LlmJobResult.CANCELLED); assertEquals(1, api.destroys)
        }
    }
    @Test fun closeFailureReportsUnavailableAndCompletionBarrierFollowsDestroy() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api(); api.onDestroy = { throw IllegalStateException("synthetic detail") }
            val job = submit(f, c, q, api)!!; q.drain(); result(job, LlmJobResult.UNAVAILABLE)
            assertEquals(ControllerState.ERROR, c.state()); assertEquals(1, api.destroys)
        }
    }
    @Test fun routePauseEndAndInterruptRevokeQueuedTickets() {
        Fixture().use { f ->
            for (transition in listOf<(NativeController) -> Unit>(
                { it.routeDisconnected() }, { it.dispatch(ControllerEvent.PAUSE) }, { it.endConversation() },
                { it.interruptReply(it.token()!!) { true } },
            )) {
                val c = controller(); val q = Queue(); val api = Api()
                val job = submit(f, c, q, api)!!; transition(c); q.drain(); result(job, LlmJobResult.CANCELLED)
                assertEquals(0, api.creates)
            }
        }
    }
    @Test fun joinFromControllerMonitorIsRefusedAndCompletedJobDoesNotOccupyTicket() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val job = submit(f, c, q)!!; joinTarget = job
            assertNull(jobJoinFromController(c)); q.drain(); result(job, LlmJobResult.COMPLETED)
            val second = submit(f, c, q)!!; q.drain(); result(second, LlmJobResult.COMPLETED)
            assertNull(job.awaitCompletion(-1, TimeUnit.SECONDS))
        }
    }
    @Test fun backendOverrunCannotReleaseMoreThanRequestedPieces() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); var released = 0
            val api = object : Api() {
                override fun next(handle: Long, output: ByteArray, count: IntArray): Int {
                    borrowedPiece = output; output[0] = 66; count[0] = 1; return 1
                }
            }
            val job = submit(f, c, q, api, limit = 1, consume = { _, _ -> released++ })!!
            q.drain(); result(job, LlmJobResult.UNAVAILABLE); assertEquals(1, released)
            assertTrue(api.borrowedPiece!!.all { it == 0.toByte() }); assertEquals(1, api.destroys)
        }
    }
    @Test fun descriptorCloseRevocationCannotPublishOrBeginModel() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api(); f.onClose = { c.privacyTransition(PrivacyChange.LOCK) }
            val job = submit(f, c, q, api)!!; q.drain(); result(job, LlmJobResult.CANCELLED)
            assertEquals(0, api.begins); assertEquals(1, api.destroys); assertEquals(1, f.closes)
        }
    }
    @Test fun deniedOrBrokenThreadEligibilityFinishesWithoutOpeningModel() {
        Fixture().use { f ->
            for (guard in listOf<() -> Boolean>({ false }, { throw IllegalStateException("synthetic detail") })) {
                val c = controller(); val q = Queue(); val prompt = byteArrayOf(65)
                val job = LlmControllerJob.submit(c, c.token()!!, q, f.store, f.selection, prompt, api = Api(),
                    openDescriptor = f::open, workerThreadAllowed = guard, consume = { _, _ -> fail() })!!
                q.drain(); result(job, LlmJobResult.UNAVAILABLE); assertEquals(0, prompt[0].toInt()); assertEquals(0, f.opens)
            }
        }
    }
    @Test fun stopDuringFinalDestroyCannotPublishSuccessfulCompletion() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api().apply { onDestroy = { c.stop() } }
            val job = submit(f, c, q, api)!!; q.drain(); result(job, LlmJobResult.CANCELLED)
            assertEquals(ControllerState.STOPPED, c.state()); assertEquals(1, api.destroys)
        }
    }
    @Test fun packRevocationAtEndOfStreamCannotPublishSuccessfulCompletion() {
        Fixture().use { f ->
            val c = controller(); val q = Queue(); val api = Api().apply { onDestroy = { f.activate() } }
            val job = submit(f, c, q, api)!!; q.drain(); result(job, LlmJobResult.UNAVAILABLE)
            assertEquals(ControllerState.ERROR, c.state()); assertEquals(1, api.destroys)
        }
    }    @Test fun queuedGenericRequestClearsBeforeWorkerOnStopAndPrivacy(){for(change in listOf(null,PrivacyChange.LOCK,PrivacyChange.PRIVATE_SESSION,PrivacyChange.IDENTITY_RESET)){Fixture().use{f->val c=controller();val q=Queue();val request=GenericReplyRequest("Synthetic request",listOf(QwenTurn(QwenRole.ASSISTANT,"Synthetic context")));val prompt=byteArrayOf(65);val job=LlmControllerJob.submit(c,c.token()!!,q,f.store,f.selection,prompt,api=Api(),openDescriptor=f::open,workerThreadAllowed={true},request=request,consume={_,_->fail("cancelled output")})!!;if(change==null)c.stop()else c.privacyTransition(change);assertTrue(request.latest.isEmpty());assertTrue(request.history.isEmpty());assertTrue(prompt.all{it==0.toByte()});assertEquals(0,f.opens);q.drain();result(job,LlmJobResult.CANCELLED);assertEquals(0,f.opens)}}}

}
