package com.eilo.foundation

import java.io.File
import java.nio.file.Files
import java.security.KeyPairGenerator
import java.security.MessageDigest
import java.security.Signature
import java.security.spec.ECGenParameterSpec
import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

class LlmPackLeaseTest {
    private class Fixture : AutoCloseable {
        val root = Files.createTempDirectory("eilo-llm-pack").toFile()
        val source = File(root, "source").apply { writeBytes(byteArrayOf(1, 2, 3, 4)) }
        val decoy = File(root, "decoy").apply { writeBytes(byteArrayOf(5, 6)) }
        val runtime = "a".repeat(40); val evidence = "c".repeat(64)
        val key = KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()
        val trust = mapOf("test-key" to key.public.encoded)
        val store = PackStore(File(root, "store"), trust, runtime, setOf(evidence))
        val pin = LlmArtifactPin("model", digest(source), 4, evidence)
        val selection = LlmPackSelection("test-pack", runtime, pin)
        fun pack(revision: Int = 1, role: String = "llm", filename: String = "model.gguf", license: String = "Apache-2.0"): VerifiedPack {
            fun artifact(id: String, name: String, kind: String, file: File, rights: String = "Apache-2.0") =
                JSONObject().put("id", id).put("filename", name).put("role", kind).put("url", "https://models.example.test/$name")
                    .put("sha256", digest(file)).put("bytes", file.length()).put("license", rights).put("licenseEvidence", evidence)
            val files = JSONArray().put(artifact("decoy", "decoy.txt", "tokenizer", decoy))
                .put(artifact("model", filename, role, source, license))
            val bytes = JSONObject().put("schema", 1).put("packId", "test-pack").put("revision", revision)
                .put("runtimeRevision", runtime).put("minAndroid", 35).put("minIos", 18).put("artifacts", files).toString().toByteArray()
            val signer = Signature.getInstance("SHA256withECDSA"); signer.initSign(key.private); signer.update(bytes)
            return VerifiedPack.verify(bytes, signer.sign(), "test-key", "ES256", trust, runtime)
        }
        fun activate(pack: VerifiedPack = pack()) {
            store.activate(pack, pack.manifest.artifacts.mapIndexed { index, item ->
                VerifiedArtifact.verify(pack, index, if (item.id == "model") source else decoy)
            }, PackCancellation())
        }
        fun lease() = LlmPackLease.resolve(store, selection)
        override fun close() { root.deleteRecursively() }
        companion object {
            fun digest(file: File) = MessageDigest.getInstance("SHA-256").digest(file.readBytes()).joinToString("") { "%02x".format(it) }
        }
    }
    private class Api : NativeLlmApi {
        var creates = 0; var loads = 0; var destroys = 0; var nexts = 0
        var onCreate: () -> Unit = {}; var onLoad: () -> Int = { 0 }; var onNext: () -> Unit = {}
        override fun create(): Long { creates++; onCreate(); return 7L }
        override fun load(handle: Long, descriptor: Int, threads: Int): Int {
            loads++; assertEquals(31, descriptor); return onLoad()
        }
        override fun begin(handle: Long, prompt: ByteArray, count: Int, outputLimit: Int) = 0
        override fun next(handle: Long, output: ByteArray, count: IntArray): Int {
            nexts++; output[0] = 65; count[0] = 1; onNext(); return 1
        }
        override fun cancel(handle: Long) {}
        override fun destroy(handle: Long) { destroys++ }
    }
    private class Opening {
        var opens = 0; var closes = 0; var onOpen: () -> Unit = {}; var onClose: () -> Unit = {}
        fun open(file: File, pin: LlmArtifactPin): LlmVerifiedDescriptor {
            opens++; assertEquals("model.gguf", file.name); assertEquals(pin.sha256, Fixture.digest(file))
            onOpen(); return LlmVerifiedDescriptor(31) { closes++; onClose() }
        }
    }
    private fun rejects(action: () -> Unit) {
        try { action(); fail("invalid model lease accepted") } catch (error: LlmFailure) {
            assertEquals("LLM unavailable", error.message); assertNull(error.cause)
        }
    }
    @Test fun exactSignedIdSelectsModelAfterShuffledDecoyAndClosesDescriptor() {
        Fixture().use { f ->
            f.activate(); val lease = f.lease(); val api = Api(); val fd = Opening()
            val stream = lease.openStream({ true }, api = api, openDescriptor = fd::open)
            assertEquals(1, api.creates); assertEquals(1, api.loads); assertEquals(1, fd.closes)
            stream.begin(byteArrayOf(65), 8); assertTrue(stream.withNextPiece { out, n -> assertEquals(65, out[0].toInt()); assertEquals(1, n) })
            stream.close(); lease.close(); assertFalse(lease.verified()); assertEquals(1, api.destroys)
        }
    }
    @Test fun missingUntrustedAndUnlicensedStoreCannotResolve() {
        Fixture().use { f ->
            rejects { f.lease() }; f.activate()
            for (store in listOf(PackStore(File(f.root, "store"), emptyMap(), f.runtime, setOf(f.evidence)),
                PackStore(File(f.root, "store"), f.trust, f.runtime))) rejects { LlmPackLease.resolve(store, f.selection) }
        }
    }
    @Test fun readOnlyVerifiedSourceCanActivateWithoutEnablingWrites() {
        Fixture().use { f ->
            assertTrue(f.source.setReadOnly()); f.activate()
            assertTrue(f.lease().verified()); assertFalse(f.source.canWrite())
            val current = f.store.active()!!; assertFalse(f.store.file(current, 1).canWrite())
        }
    }
    @Test fun rejectsWrongPackRuntimeIdHashSizeAndLicenseEvidence() {
        Fixture().use { f ->
            f.activate()
            for (selection in listOf(f.selection.copy(packId = "other"), f.selection.copy(runtimeRevision = "b".repeat(40)),
                f.selection.copy(model = f.pin.copy(id = "absent")), f.selection.copy(model = f.pin.copy(sha256 = "d".repeat(64))),
                f.selection.copy(model = f.pin.copy(bytes = 5)), f.selection.copy(model = f.pin.copy(licenseEvidence = "d".repeat(64))))) {
                rejects { LlmPackLease.resolve(f.store, selection) }
            }
        }
    }
    @Test fun signedWrongRoleExtensionOrLicenseAreRejected() {
        Fixture().use { f ->
            f.activate(f.pack(role = "asr")); rejects { f.lease() }
            f.activate(f.pack(2, filename = "model.onnx")); rejects { f.lease() }
            f.activate(f.pack(3, license = "MIT")); rejects { f.lease() }
        }
    }
    @Test fun corruptSignedArtifactAndSymlinkAreRejected() {
        Fixture().use { f ->
            f.activate(); val pack = f.store.active()!!; val target = f.store.file(pack, 1)
            target.writeBytes(byteArrayOf(9, 9, 9, 9)); rejects { f.lease() }
            target.delete(); Files.createSymbolicLink(target.toPath(), f.source.toPath()); rejects { f.lease() }
        }
    }
    @Test fun closedLeaseAndInvalidThreadsRejectBeforeDescriptorOrApi() {
        Fixture().use { f ->
            f.activate(); val lease = f.lease(); val api = Api(); val fd = Opening()
            for (threads in listOf(0, 9)) rejects { lease.openStream({ true }, threads, api, fd::open) }
            lease.close(); lease.close(); rejects { lease.openStream({ true }, api = api, openDescriptor = fd::open) }
            assertEquals(0, fd.opens); assertEquals(0, api.creates)
        }
    }
    @Test fun rejectedControllerAndControllerExceptionsDoNotTouchModel() {
        Fixture().use { f ->
            f.activate(); val lease = f.lease(); val api = Api(); val fd = Opening()
            rejects { lease.openStream({ false }, api = api, openDescriptor = fd::open) }
            rejects { lease.openStream({ throw IllegalStateException("synthetic detail") }, api = api, openDescriptor = fd::open) }
            assertEquals(0, fd.opens); assertEquals(0, api.creates)
        }
    }
    @Test fun descriptorFailureDoesNotAllocateAndDefaultRuntimeStillUnavailable() {
        Fixture().use { f ->
            f.activate(); val lease = f.lease(); val api = Api(); val fd = Opening()
            rejects { lease.openStream({ true }, api = api, openDescriptor = { _, _ -> throw IllegalStateException("synthetic detail") }) }
            assertEquals(0, api.creates)
            rejects { lease.openStream({ true }, openDescriptor = fd::open) }; assertEquals(1, fd.closes)
        }
    }
    @Test fun revocationDuringDescriptorOpeningClosesBeforeNativeCreate() {
        Fixture().use { f ->
            f.activate(); val lease = f.lease(); val api = Api(); val fd = Opening().apply { onOpen = lease::close }
            rejects { lease.openStream({ true }, api = api, openDescriptor = fd::open) }
            assertEquals(1, fd.closes); assertEquals(0, api.creates)
        }
    }
    @Test fun replacementAndFailedActivationRevokeBorrowEvenWithUnchangedModel() {
        Fixture().use { f ->
            f.activate(); val lease = f.lease(); f.activate(f.pack(2)); assertFalse(lease.verified())
            val next = f.lease()
            try { f.activate(f.pack(1)); fail() } catch (_: Exception) { }
            assertFalse(next.verified())
        }
    }
    @Test fun replacementDuringNativeCreateOrLoadNeverPublishesHandle() {
        for (phase in listOf("create", "load")) Fixture().use { f ->
            f.activate(); val lease = f.lease(); val api = Api(); val fd = Opening()
            if (phase == "create") api.onCreate = { f.activate(f.pack(2)) }
            else api.onLoad = { f.activate(f.pack(2)); 0 }
            rejects { lease.openStream({ true }, api = api, openDescriptor = fd::open) }
            assertEquals(1, api.destroys); assertEquals(1, fd.closes)
        }
    }
    @Test fun closeFailureOrRevocationDuringDescriptorCloseCannotReturnLoadedStream() {
        for (fails in listOf(false, true)) Fixture().use { f ->
            f.activate(); val lease = f.lease(); val api = Api()
            val fd = Opening().apply { onClose = { if (fails) throw IllegalStateException("synthetic detail") else lease.close() } }
            rejects { lease.openStream({ true }, api = api, openDescriptor = fd::open) }
            assertEquals(1, fd.closes); assertEquals(1, api.destroys)
        }
    }
    @Test fun backendFailureClosesDescriptorAndNativeHandleExactlyOnce() {
        Fixture().use { f ->
            f.activate(); val api = Api().apply { onLoad = { -3 } }; val fd = Opening()
            rejects { f.lease().openStream({ true }, api = api, openDescriptor = fd::open) }
            assertEquals(1, fd.closes); assertEquals(1, api.destroys)
        }
    }
    @Test fun stopAndPrivacyTransitionAfterDecodeRejectRealControllerToken() {
        for (privacy in listOf(false, true)) Fixture().use { f ->
            f.activate(); val controller = testController(); controller.dispatch(ControllerEvent.START)
            val token = controller.token()!!; val api = Api(); val fd = Opening()
            val stream = f.lease().openStream({ !token.cancelled }, api = api, openDescriptor = fd::open)
            stream.begin(byteArrayOf(65), 8)
            api.onNext = { if (privacy) controller.privacyTransition(PrivacyChange.PRIVATE_SESSION) else controller.stop() }
            rejects { stream.withNextPiece { _, _ -> fail("stale piece released") } }
            assertEquals(1, api.nexts); assertEquals(1, api.destroys); stream.close()
        }
    }
    @Test fun packRevokedDuringDecodeRejectsPieceAndClosesModel() {
        Fixture().use { f ->
            f.activate(); val lease = f.lease(); val api = Api(); val fd = Opening()
            val stream = lease.openStream({ true }, api = api, openDescriptor = fd::open); stream.begin(byteArrayOf(65), 8)
            api.onNext = { f.activate(f.pack(2)) }
            rejects { stream.withNextPiece { _, _ -> fail("revoked piece released") } }; assertEquals(1, api.destroys)
        }
    }
}
