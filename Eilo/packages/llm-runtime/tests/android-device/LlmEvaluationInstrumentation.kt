package com.eilo.foundation

import android.app.Instrumentation
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.ParcelFileDescriptor
import android.os.SystemClock
import android.system.Os
import android.system.OsConstants
import java.io.File
import java.io.RandomAccessFile
import java.security.MessageDigest
import java.security.KeyPairGenerator
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import java.nio.file.Files
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference
import org.json.JSONArray
import org.json.JSONObject

internal object LlmEvaluationProbe {
    external fun cpuOnly(): Boolean
    external fun networkDenied(): Boolean
    external fun workerActive(handle: Long): Boolean
}

/** Only included by the explicit ignored Debug evaluator. No UI or microphone. */
class LlmEvaluationInstrumentation : Instrumentation() {
    private val bytes = 1282439424L
    private val hash = "c0efea3254c2363a9559e32ac76e9987aff3a68c31b84a3e65c12aa5c01bd120"
    private var stage = "initial"
    override fun onCreate(arguments: Bundle?) { super.onCreate(arguments); start() }
    private fun expect(reason: LlmFailureReason, action: () -> Unit) {
        try { action() } catch (error: LlmFailure) {
            check(error.reason == reason && error.message == "LLM unavailable" && error.cause == null)
            return
        }
        error("evaluation unavailable")
    }
    private fun descriptor(path: File, verify: Boolean): ParcelFileDescriptor {
        val original = Os.open(path.absolutePath, OsConstants.O_RDONLY or OsConstants.O_NOFOLLOW or OsConstants.O_CLOEXEC, 0)
        val fd = try { ParcelFileDescriptor.dup(original) } finally { Os.close(original) }
        try {
            val info = Os.fstat(fd.fileDescriptor)
            check(OsConstants.S_ISREG(info.st_mode) && info.st_size == bytes)
            if (verify) {
                val digest = MessageDigest.getInstance("SHA-256"); val scratch = ByteArray(65536)
                try {
                    while (true) {
                        val count = Os.read(fd.fileDescriptor, scratch, 0, scratch.size)
                        check(count >= 0); if (count == 0) break
                        digest.update(scratch, 0, count)
                    }
                    check(digest.digest().joinToString("") { "%02x".format(it) } == hash)
                    check(Os.lseek(fd.fileDescriptor, 0L, OsConstants.SEEK_SET) == 0L)
                } finally { scratch.fill(0) }
            }
            return fd // This exact hashed descriptor is borrowed by the C adapter.
        } catch (error: Exception) { fd.close(); throw error }
    }
    private fun begin(stream: NativeLlmStream, text: String) {
        val prompt = text.toByteArray(Charsets.UTF_8)
        try { stream.begin(prompt, 8) } finally { prompt.fill(0) }
    }
    private fun make(fd: Int, api: NativeLlmApi, allowed: () -> Boolean = { true }): NativeLlmStream {
        val stream = NativeLlmStream(allowed, api)
        try { stream.load(fd); return stream } catch (error: Exception) { stream.close(); throw error }
    }
    private fun concurrentCancellation(fd: Int, real: NativeLlmApi, loading: Boolean) {
        val entered = CountDownLatch(1); val cancellation = AtomicReference<Boolean?>()
        val api = object : NativeLlmApi by real {
            override fun load(handle: Long, descriptor: Int, threads: Int): Int {
                if (loading) entered.countDown()
                return real.load(handle, descriptor, threads)
            }
            override fun begin(handle: Long, prompt: ByteArray, count: Int, outputLimit: Int): Int {
                if (!loading) entered.countDown()
                return real.begin(handle, prompt, count, outputLimit)
            }
        }
        val stream = NativeLlmStream({ true }, api)
        val canceller = Thread {
            if (entered.await(10, TimeUnit.SECONDS)) { Thread.sleep(2); cancellation.set(stream.requestCancellation()) }
        }
        try {
            if (!loading) stream.load(fd)
            canceller.start()
            try {
                if (loading) stream.load(fd) else begin(stream, " A".repeat(1500))
            } catch (error: LlmFailure) { check(error.reason == LlmFailureReason.CANCELLED) }
            canceller.join(10000); check(!canceller.isAlive && cancellation.get() == true)
            expect(LlmFailureReason.CANCELLED) { stream.withNextPiece { _, _ -> error("cancelled fixture released") } }
        } finally { canceller.join(10000); stream.close() }
    }
    private fun registry(api: NativeLlmApi): List<String> {
        val ids = ArrayList<Long>()
        try {
            repeat(4) { val id = api.create(); check(id > 0 && id !in ids); ids.add(id) }
            check(api.create() == 0L)
            val id = ids[0]
            check(api.begin(id, byteArrayOf(65), 2, 8) == -1)
            check(api.begin(id, byteArrayOf(65), 0, 8) == -1)
            check(api.begin(id, ByteArray(16385), 16385, 8) == -1)
            check(api.next(id, ByteArray(1023), IntArray(1)) == -1)
            check(api.next(id, ByteArray(1024), IntArray(2)) == -1)
            api.destroy(id); ids.remove(id); api.cancel(id); api.destroy(id)
            val output = ByteArray(1024) { 65 }; val count = intArrayOf(9)
            check(api.next(id, output, count) == -1 && count[0] == 0 && output.all { it == 0.toByte() })
            val replacement = api.create(); check(replacement > 0 && replacement != id); ids.add(replacement)
            check(api.load(Long.MAX_VALUE, -1, 2) == -1)
            api.cancel(Long.MAX_VALUE); api.destroy(Long.MAX_VALUE)
        } finally { ids.forEach(api::destroy) }
        return listOf("bounded_registry", "malformed_arrays", "stale_nonreused_ids", "invalid_ids")
    }
    private fun destroyDuringLoad(fd: Int, api: NativeLlmApi): Int {
        val id = api.create(); check(id > 0)
        val entered = CountDownLatch(1); val result = AtomicReference<Int?>()
        val worker = Thread { entered.countDown(); result.set(api.load(id, fd, 2)) }
        try {
            worker.start(); check(entered.await(10, TimeUnit.SECONDS))
            val deadline = SystemClock.elapsedRealtime() + 10000
            var active = LlmEvaluationProbe.workerActive(id)
            while (!active && worker.isAlive && SystemClock.elapsedRealtime() < deadline) {
                Thread.sleep(1); active = LlmEvaluationProbe.workerActive(id)
            }
            check(active) // A pre-lookup invalid-ID rejection is not this test.
            api.destroy(id); worker.join(30000); check(!worker.isAlive)
            // The observed worker gate was held. A fast successful load may end
            // before destroy; otherwise its retained lifetime cancels safely.
            check(result.get() in listOf(0, -2))
            check(api.next(id, ByteArray(1024), IntArray(1)) == -1)
            return result.get()!!
        } finally { worker.join(30000); api.destroy(id) }
    }
    private fun descriptorChecks(work: File) {
        val small = File(work, "descriptor-fixture").apply { writeBytes(byteArrayOf(1, 2, 3, 4)) }
        val digest = MessageDigest.getInstance("SHA-256").digest(small.readBytes()).joinToString("") { "%02x".format(it) }
        val pin = LlmArtifactPin("model", digest, 4, "c".repeat(64))
        val owned = LlmModelDescriptor.open(small, pin)
        ParcelFileDescriptor.fromFd(owned.value).use { borrowed ->
            val data = ByteArray(4); check(Os.read(borrowed.fileDescriptor, data, 0, 4) == 4)
            check(data.contentEquals(byteArrayOf(1, 2, 3, 4))); data.fill(0)
        }
        owned.close(); owned.close()
        try { ParcelFileDescriptor.fromFd(owned.value).use { }; error("closed fixture descriptor reused") }
        catch (_: java.io.IOException) { }
        val symlink = File(work, "descriptor-link")
        Files.createSymbolicLink(symlink.toPath(), small.toPath())
        val fifo = File(work, "descriptor-fifo"); Os.mkfifo(fifo.absolutePath, 384)
        for ((file, selected) in listOf(small to pin.copy(sha256 = "d".repeat(64)), small to pin.copy(bytes = 5),
            symlink to pin, work to pin, fifo to pin)) {
            expect(LlmFailureReason.UNAVAILABLE) { LlmModelDescriptor.open(file, selected).close() }
        }
    }
    private class SignedPackFixture(work: File, model: File, hash: String, size: Long, progress: (String) -> Unit) {
        private val evidence = "c".repeat(64)
        private val runtime = "8345f333951c661d166b00e6f9362e553768f292"
        private val key = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()
        private val trust = mapOf("evaluation-key" to key.public.encoded)
        val store = PackStore(File(work, "signed-pack-store"), trust, runtime, setOf(evidence))
        val selection = LlmPackSelection("evaluation-pack", runtime, LlmArtifactPin("model", hash, size, evidence))
        val pack: VerifiedPack
        val proofs: List<VerifiedArtifact>
        init {
            val artifact = JSONObject().put("id", "model").put("filename", "model.gguf").put("role", "llm")
                .put("url", "https://models.example.test/model.gguf").put("sha256", hash).put("bytes", size)
                .put("license", "Apache-2.0").put("licenseEvidence", evidence)
            // Android's JSONStringer escapes URL slashes. The reviewed manifest
            // grammar deliberately accepts plain ASCII strings, so normalize this
            // fixed synthetic payload BEFORE signing; never rewrite signed input.
            val payload = JSONObject().put("schema", 1).put("packId", "evaluation-pack").put("revision", 1)
                .put("runtimeRevision", runtime).put("minAndroid", 35).put("minIos", 18)
                .put("artifacts", JSONArray().put(artifact)).toString().replace("\\/", "/").toByteArray()
            val signer = Signature.getInstance("SHA256withECDSA"); signer.initSign(key.private); signer.update(payload)
            progress("signed_manifest_signature")
            pack = VerifiedPack.verify(payload, signer.sign(), "evaluation-key", "ES256", trust, runtime)
            progress("signed_model_proof")
            proofs = listOf(VerifiedArtifact.verify(pack, 0, model))
            progress("signed_store_activation")
            store.activate(pack, proofs, PackCancellation()) { progress("signed_activation_" + it.name.lowercase()) }
        }
        fun lease() = LlmPackLease.resolve(store, selection)
        fun failActivationAndRevoke() {
            var failed = false; var boundaryReached = false
            try { store.activate(pack, proofs, PackCancellation()) { if (it == PackActivationStep.BEFORE_POINTER) {
                boundaryReached = true; error("evaluation unavailable")
            } } }
            catch (_: Exception) { failed = true }
            check(failed && boundaryReached)
        }
    }
    private fun thinkingController(): NativeController = NativeController(
        effects = object : ControllerEffects {
            override fun startCapture() = true // Synthetic state setup, no AudioRecord/microphone.
            override fun playClause(clause: String) { error("raw output not speech") }
            override fun cancelWork() {}
            override fun releaseCapture() {}
            override fun clearVolatileContext() {}
        },
        permission = object : MicrophonePermissionAdapter {
            override fun status() = MicrophonePermission.GRANTED
            override fun request(completion: (MicrophonePermission) -> Unit) { completion(status()) }
        }, models = ModelReadinessAdapter { ModelStatus.READY },
    ).apply {
        check(dispatch(ControllerEvent.START))
        check(dispatch(ControllerEvent.SPEECH_DETECTED, token = token()))
        check(dispatch(ControllerEvent.ENDPOINT, token = token()))
    }
    /** Observe the real JNI worker gate before Stop, not merely a Kotlin pre-load latch. */
    private fun controllerLoadStop(signed: SignedPackFixture, real: NativeLlmApi) {
        val controller = thinkingController()
        val worker = java.util.concurrent.Executors.newSingleThreadExecutor()
        val entered = CountDownLatch(1); val id = java.util.concurrent.atomic.AtomicLong(0)
        val destroyed = java.util.concurrent.atomic.AtomicInteger(0)
        val api = object : NativeLlmApi by real {
            override fun load(handle: Long, descriptor: Int, threads: Int): Int {
                id.set(handle); entered.countDown(); return real.load(handle, descriptor, threads)
            }
            override fun destroy(handle: Long) { real.destroy(handle); destroyed.incrementAndGet() }
        }
        val prompt = "The opposite of cold is".toByteArray()
        val job = LlmControllerJob.submit(controller, controller.token()!!, worker, signed.store, signed.selection,
            prompt, 8, api = api, consume = { _, _ -> error("stopped job released piece") }) ?: error("job unavailable")
        try {
            check(entered.await(30, TimeUnit.SECONDS))
            val deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(5)
            var active = LlmEvaluationProbe.workerActive(id.get())
            while (!active && System.nanoTime() < deadline) { Thread.sleep(1); active = LlmEvaluationProbe.workerActive(id.get()) }
            check(active)
            check(controller.stop())
            check(job.awaitCompletion(30, TimeUnit.SECONDS) == LlmJobResult.CANCELLED)
            check(destroyed.get() == 1 && prompt.all { it == 0.toByte() } && controller.state() == ControllerState.STOPPED)
        } finally {
            job.requestCancellation(); worker.shutdown()
            check(worker.awaitTermination(30, TimeUnit.SECONDS))
        }
    }
    override fun onStart() {
        val context = targetContext; val work = File(context.filesDir, "llm-evaluation")
        val report = File(context.filesDir, "llm-android-results.json")
        val result = Bundle(); var passed = false; report.delete()
        try {
            stage = "gates"
            check(context.checkSelfPermission("android.permission.INTERNET") == PackageManager.PERMISSION_DENIED)
            check(NativeLlmRuntime().load() == null && NativeLlmRuntime(true, false).load() == null)
            expect(LlmFailureReason.UNAVAILABLE) { NativeLlmStream({ true }) }
            val api = NativeLlmRuntime(true).load() ?: error("evaluation unavailable")
            check(LlmEvaluationProbe.networkDenied())
            stage = "registry"; val registryCases = registry(api)
            stage = "descriptor_validation"; descriptorChecks(work)
            stage = "signed_pack_activation"
            val signed = SignedPackFixture(work, File(work, "model.gguf"), hash, bytes) { stage = it }
            stage = "model_hash"
            descriptor(File(work, "model.gguf"), true).use { model ->
                val cases = JSONArray()
                make(model.fd,api).use { stream ->
                    val plan=PromptBudget.build("Name one colour.",List(16){QwenTurn(QwenRole.USER,"Generic earlier context. ".repeat(100))},List(6){"Generic recalled fact. ".repeat(60)},count=stream::countTokens)
                    check(plan.promptTokens+plan.outputLimit<=4096 && plan.recalledTokens<=512 && plan.droppedHistory>0 && plan.droppedRecall>0)
                    check(plan.text.contains(QwenTemplate.RULES) && plan.text.contains("Name one colour."))
                    check(stream.countTokens(plan.text)==plan.promptTokens);begin(stream,plan.text);check(stream.withNextPiece{_,_->})
                }
                val prompts = listOf("The opposite of cold is", "One, two, three,", "The sky on a clear day is")
                for ((index, prompt) in prompts.withIndex()) {
                    stage = "completion_${index + 1}"
                    val controller = thinkingController()
                    val worker = java.util.concurrent.Executors.newSingleThreadExecutor()
                    val ownedPrompt = prompt.toByteArray()
                        // Only these frozen generic outputs are copied for a report.
                        val output = ByteArray(8192); var length = 0; var tokens = 0
                        var borrowed: ByteArray? = null
                        var job: LlmControllerJob? = null
                        try {
                            job = LlmControllerJob.submit(controller, controller.token()!!, worker, signed.store, signed.selection,
                                ownedPrompt, 8, api = api, consume = { piece, n ->
                                    check(Thread.holdsLock(controller) && Thread.currentThread() !== android.os.Looper.getMainLooper().thread)
                                    check(length + n <= output.size); piece.copyInto(output, length, 0, n); length += n
                                    borrowed = piece; tokens++; check(tokens <= 8)
                                }) ?: error("job unavailable")
                            check(job.awaitCompletion(60, TimeUnit.SECONDS) == LlmJobResult.COMPLETED)
                            check(LlmEvaluationProbe.cpuOnly() && tokens > 0 && length > 0)
                            check(ownedPrompt.all { it == 0.toByte() } && borrowed!!.all { it == 0.toByte() })
                            check(controller.state() == ControllerState.THINKING) // Raw completion grants no speech.
                            cases.put(JSONObject().put("id", index + 1).put("prompt", prompt).put("tokens", tokens)
                                .put("output", output.copyOfRange(0, length).toString(Charsets.UTF_8))
                                .put("kind", "controller-worker raw completion, not speech-approved"))
                        } finally {
                            job?.requestCancellation(); worker.shutdown()
                            check(worker.awaitTermination(30, TimeUnit.SECONDS))
                            output.fill(0); ownedPrompt.fill(0)
                        }
                }
                stage = "controller_stop_during_native_load"; controllerLoadStop(signed, api)
                stage = "signed_pack_revocation"
                val signedLease = signed.lease()
                val revokePack = object : NativeLlmApi by api {
                    override fun next(handle: Long, output: ByteArray, count: IntArray): Int {
                        val status = api.next(handle, output, count); signed.failActivationAndRevoke(); return status
                    }
                }
                try { signedLease.openStream({ true }, api = revokePack).use { stream ->
                    begin(stream, prompts[0])
                    expect(LlmFailureReason.UNAVAILABLE) { stream.withNextPiece { _, _ -> error("revoked pack fixture released") } }
                    check(!signedLease.verified())
                } } finally { signedLease.close() }
                stage = "pre_cancel"
                NativeLlmStream({ true }, api).use { stream ->
                    check(stream.requestCancellation()); expect(LlmFailureReason.CANCELLED) { stream.load(model.fd) }
                }
                stage = "corrupt_gguf"
                val invalid = File(work, "invalid.gguf")
                RandomAccessFile(invalid, "rw").use { it.setLength(bytes) }
                descriptor(invalid, false).use { fd ->
                    expect(LlmFailureReason.UNAVAILABLE) { make(fd.fd, api).close() }
                }
                stage = "post_token_cancel"
                make(model.fd, api).use { stream ->
                    begin(stream, prompts[0]); check(stream.withNextPiece { _, _ -> })
                    check(stream.requestCancellation())
                    expect(LlmFailureReason.CANCELLED) { stream.withNextPiece { _, _ -> error("cancelled fixture released") } }
                }
                stage = "lease_revocation"
                var allowed = true
                val revoke = object : NativeLlmApi by api {
                    override fun next(handle: Long, output: ByteArray, count: IntArray): Int {
                        val status = api.next(handle, output, count); allowed = false; return status
                    }
                }
                make(model.fd, revoke, { allowed }).use { stream ->
                    begin(stream, prompts[0])
                    expect(LlmFailureReason.UNAVAILABLE) { stream.withNextPiece { _, _ -> error("revoked fixture released") } }
                }
                stage = "concurrent_load_cancel"; concurrentCancellation(model.fd, api, true)
                stage = "concurrent_begin_cancel"; concurrentCancellation(model.fd, api, false)
                stage = "destroy_during_load"; val destroyStatus = destroyDuringLoad(model.fd, api)
                report.writeText(JSONObject().put("task", "VC-LLM-01")
                    .put("platform", "Android API35 ARM64 emulator / actual Kotlin ART JNI CPU")
                    .put("same_open_model_descriptor_SHA256", "PASS").put("CPU_registry_only", "PASS")
                    .put("INTERNET_permission", "ABSENT").put("network_probes", "DENIED")
                    .put("model_sha256", hash).put("cases", cases).put("registry_cases", JSONArray(registryCases))
                    .put("destroy_load_worker_gate_observed", true).put("destroy_load_native_status", destroyStatus)
                    .put("pack_lease_cases", JSONArray(listOf("signed_pack_descriptor_generation", "failed_activation_rejects_raw_piece",
                        "descriptor_hash_size_symlink_directory_fifo_and_close")))
                    .put("pack_trust", "Ephemeral synthetic test key/license evidence only; no production trust configured")
                    .put("controller_worker_cases", JSONArray(listOf("signed_pack_worker_three_completions",
                        "controller_stop_during_observed_native_load", "owned_prompt_and_borrowed_piece_erased",
                        "completion_keeps_thinking_without_speech")))
                    .put("native_lifecycle_cases", JSONArray(listOf("pre_cancel", "corrupt_gguf", "post_token_cancel",
                        "lease_revocation", "concurrent_load_cancel", "concurrent_begin_cancel", "destroy_during_load")))
                    .put("default_gate_cases", JSONArray(listOf("ordinary_debug", "debug_with_release_flag", "unavailable_api")))
                    .put("prompt_budget", "Actual loaded vocabulary; context4096/recall512/output256 and deterministic trim PASS").put("microphone", "NOT USED").put("remaining", JSONArray(listOf("Swift controller worker and production app attachment",
                        "physical performance", "non-thinking configuration", "speech policy", "vendor allocator/logits erasure")))
                    .toString(2))
            }
            result.putString("eilo_llm_evaluation", "PASS"); passed = true
        } catch (error: Exception) {
            result.putString("eilo_llm_evaluation", "FAIL"); result.putString("eilo_llm_stage", stage)
            val errno = (error.cause as? android.system.ErrnoException)?.errno
            result.putString("eilo_llm_file_failure", when (errno) {
                OsConstants.EACCES -> "permission_denied"
                OsConstants.EISDIR -> "directory_open"
                else -> "unavailable"
            })
            result.putString("eilo_llm_failure_type", when (error) {
                is java.io.IOException -> "file_io"
                is IllegalArgumentException -> "invalid_argument"
                is IllegalStateException -> "invalid_state"
                is java.security.GeneralSecurityException -> "signature"
                else -> "unavailable"
            })
        } catch (_: LinkageError) {
            result.putString("eilo_llm_evaluation", "FAIL"); result.putString("eilo_llm_stage", stage)
        } finally {
            if (!work.deleteRecursively()) { passed = false; result.putString("eilo_llm_evaluation", "FAIL") }
            if (!passed) report.delete()
        }
        finish(if (passed) -1 else 0, result)
    }
}
