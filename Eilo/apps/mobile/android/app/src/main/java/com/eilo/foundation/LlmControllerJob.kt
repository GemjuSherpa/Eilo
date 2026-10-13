package com.eilo.foundation

import android.os.Looper
import java.io.File
import java.util.concurrent.CountDownLatch
import java.util.concurrent.Executor
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference

internal class LlmWorkTicket internal constructor(
    val controller: NativeController, val token: GenerationToken, val cancel: () -> Boolean,
) { @Volatile var cancelled = false }

internal enum class LlmJobResult { COMPLETED, CANCELLED, UNAVAILABLE }

/** One job owns the transferred prompt and stream on a separate native worker.
 * Cancel is a short concurrent signal; only the worker destroys/clears native work.
 * Await completion off UI/controller/capture threads before releasing worker resources.
 * Raw borrowed consumers grant no speech rights and must not retain the scratch.
 * Defaults do not enable a runtime, model readiness, microphone or app caller.
 */
internal class LlmControllerJob private constructor(
    private val controller: NativeController,
    private val prompt: ByteArray,
    private val completion:(LlmJobResult)->Unit,
) {
    private val cancelled = AtomicBoolean(false)
    private val promptGate = Any()
    private var promptBorrowed = false
    private val stream = AtomicReference<NativeLlmStream?>()
    private val done = CountDownLatch(1)
    @Volatile private var result: LlmJobResult? = null

    fun requestCancellation(): Boolean {
        synchronized(promptGate) {
            cancelled.set(true)
            if (!promptBorrowed) prompt.fill(0)
        }
        return stream.get()?.requestCancellation() ?: true
    }

    /** Lifecycle join barrier, never called from a controller transaction. */
    fun awaitCompletion(timeout: Long, unit: TimeUnit): LlmJobResult? {
        if (Thread.holdsLock(controller) || timeout < 0) return null
        return if (done.await(timeout, unit)) result else null
    }

    private fun current(ticket: LlmWorkTicket): Boolean =
        !cancelled.get() && controller.llmWorkAllowed(ticket)

    private fun run(ticket: LlmWorkTicket, store: PackStore, selection: LlmPackSelection,
        threads: Int, limit: Int, api: NativeLlmApi, request:GenericReplyRequest?,
        openDescriptor: (File, LlmArtifactPin) -> LlmVerifiedDescriptor,
        consume: (ByteArray, Int) -> Unit,
    ) {
        var lease: LlmPackLease? = null
        var outcome = LlmJobResult.UNAVAILABLE
        var cleanupFailed = false
        try {
            if (!current(ticket)) { outcome = LlmJobResult.CANCELLED; return }
            val verified = LlmPackLease.resolve(store, selection); lease = verified
            val loaded = verified.openStream({ current(ticket) }, threads, api, openDescriptor) { candidate ->
                stream.set(candidate)
                if (!current(ticket)) candidate.requestCancellation()
            }
            synchronized(promptGate) {
                if (cancelled.get() || ticket.cancelled || ticket.token.cancelled) throw LlmFailure(LlmFailureReason.CANCELLED)
                promptBorrowed = true
            }
            try {
                if(request==null)loaded.begin(prompt,limit) else {
                    val plan=PromptBudget.build(request.latest,history=request.history,outputLimit=limit,count=loaded::countTokens)
                    val planned=plan.text.toByteArray(Charsets.UTF_8)
                    try { if(!current(ticket))throw LlmFailure(LlmFailureReason.CANCELLED);loaded.begin(planned,limit) } finally {planned.fill(0)}
                }
            }
            finally { synchronized(promptGate) { prompt.fill(0); promptBorrowed = false } }
            var pieces = 0
            while (loaded.withNextPiece { bytes, count ->
                if (pieces >= limit) throw LlmFailure(LlmFailureReason.UNAVAILABLE)
                if (!controller.consumeLlmPiece(ticket, { verified.verified() && !cancelled.get() }, bytes, count, consume)) {
                    requestCancellation()
                    throw LlmFailure(LlmFailureReason.CANCELLED)
                }
                pieces++
            }) { /* native and worker independently enforce the output limit */ }
            outcome = if (!current(ticket)) LlmJobResult.CANCELLED else if (verified.verified()) LlmJobResult.COMPLETED else LlmJobResult.UNAVAILABLE
        } catch (_: LinkageError) { outcome = LlmJobResult.UNAVAILABLE }
        catch (_: Exception) { outcome = if (cancelled.get() || ticket.cancelled || ticket.token.cancelled) LlmJobResult.CANCELLED else LlmJobResult.UNAVAILABLE }
        finally {
            synchronized(promptGate) { prompt.fill(0); promptBorrowed = false }
            try { stream.getAndSet(null)?.close() } catch (_: Exception) { cleanupFailed = true; outcome = LlmJobResult.UNAVAILABLE }
            if (cancelled.get() || ticket.cancelled || ticket.token.cancelled) outcome = LlmJobResult.CANCELLED
            val accepted = controller.finishLlmWork(ticket, outcome) { lease?.verified() == true && !cancelled.get() }
            lease?.close()
            result = if (cleanupFailed) LlmJobResult.UNAVAILABLE else accepted
            done.countDown();completion(result!!) // Native destruction/prompt cleanup/controller detachment all precede this barrier.
        }
    }

    companion object {
        /** Ownership of prompt transfers even on rejection; caller must cease all access.
         * Executor must schedule on a separate native thread, never an inline/UI executor.
         * Descriptor injection is an internal synthetic-test seam, not an app trust bypass. */
        fun submit(controller: NativeController, token: GenerationToken, worker: Executor,
            store: PackStore, selection: LlmPackSelection, prompt: ByteArray, outputLimit: Int = 256,
            threads: Int = 2, api: NativeLlmApi = UnavailableLlmApi,
            openDescriptor: (File, LlmArtifactPin) -> LlmVerifiedDescriptor = LlmModelDescriptor::open,
            workerThreadAllowed: () -> Boolean = { Thread.currentThread() !== Looper.getMainLooper()?.thread },
            request:GenericReplyRequest?=null,completion:(LlmJobResult)->Unit={},
            consume: (ByteArray, Int) -> Unit,
        ): LlmControllerJob? {
            if (prompt.size !in 1..16384 || prompt.any { it == 0.toByte() } || outputLimit !in 1..256 || threads !in 1..8) {
                prompt.fill(0); return null
            }
            val job = LlmControllerJob(controller, prompt,completion)
            val ticket = controller.prepareLlmWork(token, job::requestCancellation)
            if (ticket == null) { prompt.fill(0); return null }
            val submittingThread = Thread.currentThread()
            try {
                worker.execute {
                    val separateWorker = try { Thread.currentThread() !== submittingThread && workerThreadAllowed() }
                        catch (_: LinkageError) { false } catch (_: Exception) { false }
                    if (!separateWorker) {
                        // Reject inline executors before store hashing/native create.
                        prompt.fill(0)
                        job.result = controller.finishLlmWork(ticket, LlmJobResult.UNAVAILABLE); job.done.countDown();completion(job.result!!)
                    } else job.run(ticket, store, selection, threads, outputLimit, api, request, openDescriptor, consume)
                }
            } catch (_: Exception) {
                prompt.fill(0); job.result = controller.finishLlmWork(ticket, LlmJobResult.UNAVAILABLE); job.done.countDown();completion(job.result!!)
            }
            return job
        }
    }
}
