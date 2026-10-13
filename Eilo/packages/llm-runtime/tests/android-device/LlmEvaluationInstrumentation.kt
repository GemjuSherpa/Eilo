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
            stage = "model_hash"
            descriptor(File(work, "model.gguf"), true).use { model ->
                val cases = JSONArray()
                val prompts = listOf("The opposite of cold is", "One, two, three,", "The sky on a clear day is")
                for ((index, prompt) in prompts.withIndex()) {
                    stage = "completion_${index + 1}"
                    make(model.fd, api).use { stream ->
                        check(LlmEvaluationProbe.cpuOnly()); begin(stream, prompt)
                        // Only these frozen generic outputs are copied for a report.
                        val output = ByteArray(8192); var length = 0; var tokens = 0
                        try {
                            while (stream.withNextPiece { piece, n ->
                                check(length + n <= output.size); piece.copyInto(output, length, 0, n); length += n
                            }) { tokens++; check(tokens <= 8) }
                            check(tokens > 0 && length > 0)
                            cases.put(JSONObject().put("id", index + 1).put("prompt", prompt).put("tokens", tokens)
                                .put("output", output.copyOfRange(0, length).toString(Charsets.UTF_8))
                                .put("kind", "raw completion, not speech-approved"))
                        } finally { output.fill(0) }
                    }
                }
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
                    .put("native_lifecycle_cases", JSONArray(listOf("pre_cancel", "corrupt_gguf", "post_token_cancel",
                        "lease_revocation", "concurrent_load_cancel", "concurrent_begin_cancel", "destroy_during_load")))
                    .put("default_gate_cases", JSONArray(listOf("ordinary_debug", "debug_with_release_flag", "unavailable_api")))
                    .put("microphone", "NOT USED").put("remaining", JSONArray(listOf("production pack/controller attachment",
                        "physical performance", "non-thinking configuration", "speech policy", "vendor allocator/logits erasure")))
                    .toString(2))
            }
            result.putString("eilo_llm_evaluation", "PASS"); passed = true
        } catch (_: Exception) {
            result.putString("eilo_llm_evaluation", "FAIL"); result.putString("eilo_llm_stage", stage)
        } catch (_: LinkageError) {
            result.putString("eilo_llm_evaluation", "FAIL"); result.putString("eilo_llm_stage", stage)
        } finally {
            if (!work.deleteRecursively()) { passed = false; result.putString("eilo_llm_evaluation", "FAIL") }
            if (!passed) report.delete()
        }
        finish(if (passed) -1 else 0, result)
    }
}
