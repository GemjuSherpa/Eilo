package com.eilo.foundation

import android.os.ParcelFileDescriptor
import android.os.Build
import android.system.Os
import android.system.OsConstants
import java.io.File
import java.io.FileDescriptor
import java.security.MessageDigest
import java.util.UUID

/** Reviewed native configuration only; no selection is received through JS. */
internal data class LlmArtifactPin(val id: String, val sha256: String, val bytes: Long, val licenseEvidence: String) {
    init {
        require(id.matches(Regex("[a-z0-9][a-z0-9-]{0,63}")))
        require(sha256.matches(Regex("[a-f0-9]{64}")) && licenseEvidence.matches(Regex("[a-f0-9]{64}")))
        require(bytes in 1..8_000_000_000L)
    }
}
internal data class LlmPackSelection(val packId: String, val runtimeRevision: String, val model: LlmArtifactPin) {
    init {
        require(packId.matches(Regex("[a-z0-9][a-z0-9-]{0,63}")))
        require(runtimeRevision.matches(Regex("[a-f0-9]{40}")))
    }
}

/** An exclusively owned descriptor whose SAME open file has been hashed.
 * Injectable opening is a native test seam, never a JS/platform trust bypass.
 */
internal class LlmVerifiedDescriptor(val value: Int, private val release: () -> Unit) : AutoCloseable {
    private var closed = false
    override fun close() {
        if (closed) return
        closed = true
        try { release() } catch (_: Exception) { throw LlmFailure(LlmFailureReason.UNAVAILABLE) }
    }
}

internal object LlmModelDescriptor {
    fun open(file: File, pin: LlmArtifactPin): LlmVerifiedDescriptor {
        // Atomic duplication/flag verification uses public fcntlInt from API30.
        // Keep the app's API26 floor; older model opens fail closed.
        if (Build.VERSION.SDK_INT < 30) throw LlmFailure(LlmFailureReason.UNAVAILABLE)
        var original: FileDescriptor? = null
        var owned: ParcelFileDescriptor? = null
        val scratch = ByteArray(65536)
        try {
            val raw = Os.open(file.absolutePath, OsConstants.O_RDONLY or OsConstants.O_NOFOLLOW or
                OsConstants.O_CLOEXEC or OsConstants.O_NONBLOCK, 0)
            original = raw
            // Plain dup need not preserve FD_CLOEXEC. Duplicate atomically with
            // the flag, then adopt that exact descriptor without another dup.
            owned = ParcelFileDescriptor.adoptFd(Os.fcntlInt(raw, OsConstants.F_DUPFD_CLOEXEC, 0))
            original = null; Os.close(raw)
            val fd = owned.fileDescriptor; val info = Os.fstat(fd)
            check(Os.fcntlInt(fd, OsConstants.F_GETFD, 0) and OsConstants.FD_CLOEXEC != 0)
            check(OsConstants.S_ISREG(info.st_mode) && info.st_size == pin.bytes)
            val digest = MessageDigest.getInstance("SHA-256"); var total = 0L
            while (true) {
                val count = Os.read(fd, scratch, 0, scratch.size)
                check(count >= 0); if (count == 0) break
                total += count; check(total <= pin.bytes); digest.update(scratch, 0, count)
            }
            check(total == pin.bytes && Os.fstat(fd).st_size == pin.bytes)
            check(digest.digest().joinToString("") { "%02x".format(it) } == pin.sha256)
            check(Os.lseek(fd, 0L, OsConstants.SEEK_SET) == 0L)
            val retained = owned; owned = null
            return LlmVerifiedDescriptor(retained.fd) { retained.close() }
        } catch (_: Exception) { throw LlmFailure(LlmFailureReason.UNAVAILABLE) }
        finally {
            scratch.fill(0)
            try { original?.let(Os::close) } catch (_: Exception) { }
            try { owned?.close() } catch (_: Exception) { }
        }
    }
}

/** Resolve/open on a native worker. Borrow-time checks are disk-free. Known file
 * maintenance must revoke before writes; app-private slots remain immutable.
 * Revoking a lease rejects subsequent pieces but does not wait for or interrupt
 * an active call: the controller separately signals stream.requestCancellation.
 */
internal class LlmPackLease private constructor(
    private val store: PackStore, private val epoch: UUID,
    private val file: File, private val pin: LlmArtifactPin,
) {
    @Volatile private var active = true
    fun verified(): Boolean = active && store.epoch() == epoch
    fun close() { active = false }

    fun openStream(
        allowed: () -> Boolean, threads: Int = 2, api: NativeLlmApi = UnavailableLlmApi,
        openDescriptor: (File, LlmArtifactPin) -> LlmVerifiedDescriptor = LlmModelDescriptor::open,
    ): NativeLlmStream {
        fun current() = verified() && try { allowed() } catch (_: Exception) { false }
        var stream: NativeLlmStream? = null
        try {
            check(current() && threads in 1..8)
            openDescriptor(file, pin).use { descriptor ->
                check(current() && descriptor.value >= 0)
                val candidate = NativeLlmStream(::current, api); stream = candidate
                candidate.load(descriptor.value, threads)
            }
            check(current()) // Descriptor-close failure/revocation cannot publish a stream.
            return stream ?: throw LlmFailure(LlmFailureReason.UNAVAILABLE)
        } catch (error: Exception) {
            try { stream?.close() } catch (_: Exception) { }
            throw LlmFailure(if (error is LlmFailure) error.reason else LlmFailureReason.UNAVAILABLE)
        } catch (_: LinkageError) {
            try { stream?.close() } catch (_: Exception) { }
            throw LlmFailure(LlmFailureReason.UNAVAILABLE)
        }
    }

    companion object {
        fun resolve(store: PackStore, selection: LlmPackSelection): LlmPackLease {
            try {
                val epoch = store.epoch()
                val snapshot = store.verifiedFiles() ?: error("unavailable")
                val manifest = snapshot.first.manifest
                check(manifest.packId == selection.packId && manifest.runtimeRevision == selection.runtimeRevision)
                val index = manifest.artifacts.indexOfFirst { it.id == selection.model.id }
                check(index >= 0)
                val artifact = manifest.artifacts[index]; val pin = selection.model
                check(artifact.role == "llm" && artifact.filename.endsWith(".gguf") &&
                    artifact.sha256 == pin.sha256 && artifact.bytes == pin.bytes &&
                    artifact.license == "Apache-2.0" && artifact.licenseEvidence == pin.licenseEvidence)
                check(store.epoch() == epoch)
                return LlmPackLease(store, epoch, snapshot.second[index], pin)
            } catch (_: Exception) { throw LlmFailure(LlmFailureReason.UNAVAILABLE) }
        }
    }
}
