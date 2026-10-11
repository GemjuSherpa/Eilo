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

class WakePackLeaseTest {
    private val configuration=WakeConfiguration("HEY EILO",0.125f,1.5f)
    private class Fixture : AutoCloseable {
        val root=Files.createTempDirectory("eilo-wake-pack").toFile()
        private val key=KeyPairGenerator.getInstance("EC").apply { initialize(ECGenParameterSpec("secp256r1")) }.generateKeyPair()
        private val trust=mapOf("test-key" to key.public.encoded)
        val store=PackStore(File(root,"store"),trust,PackFixtures.runtime,setOf("c".repeat(64)))
        val ids=listOf("encoder","decoder","joiner","tokens")
        val source=ids.mapIndexed { n,id -> File(root,id).apply { writeBytes(byteArrayOf(1,2,3,(n+4).toByte())) } }
        val pins=ids.mapIndexed { n,id -> WakeArtifactPin(id,MessageDigest.getInstance("SHA-256").digest(source[n].readBytes()).joinToString("") { "%02x".format(it) }) }
        val selection=WakePackSelection("test-pack",PackFixtures.runtime,pins[0],pins[1],pins[2],pins[3])
        fun pack(revision: Int=1, wrongRole: Boolean=false, omit: Boolean=false): VerifiedPack {
            val artifacts=JSONArray()
            // Deliberately shuffled: resolution must use IDs, not positions.
            for(n in listOf(3,1,0,2)) {
                if(omit && n==2)continue
                artifacts.put(JSONObject().put("id",ids[n]).put("filename",ids[n]+if(n==3) ".txt" else ".onnx")
                    .put("role",if(wrongRole && n==0) "asr" else if(n==3) "tokenizer" else "wake")
                    .put("url","https://models.example.test/${ids[n]}").put("sha256",pins[n].sha256)
                    .put("bytes",4).put("license","Apache-2.0").put("licenseEvidence","c".repeat(64)))
            }
            val bytes=JSONObject().put("schema",1).put("packId","test-pack").put("revision",revision)
                .put("runtimeRevision",PackFixtures.runtime).put("minAndroid",35).put("minIos",18).put("artifacts",artifacts).toString().toByteArray()
            val signer=Signature.getInstance("SHA256withECDSA");signer.initSign(key.private);signer.update(bytes)
            return VerifiedPack.verify(bytes,signer.sign(),"test-key","ES256",trust,PackFixtures.runtime)
        }
        fun activate(pack: VerifiedPack=pack()) {
            store.activate(pack,pack.manifest.artifacts.mapIndexed { n,a -> VerifiedArtifact.verify(pack,n,source[ids.indexOf(a.id)]) },PackCancellation())
        }
        override fun close() { root.deleteRecursively() }
    }
    private class API(private val onCreate: ()->Unit={}) : NativeWakeAPI {
        @Volatile var creates=0;@Volatile var destroys=0;@Volatile var processes=0;var paths:WakeModelPaths?=null
        var onProcess: ()->Unit={}
        override fun create(paths: WakeModelPaths,configuration: WakeConfiguration): Long { creates++;this.paths=paths;onCreate();return 7L }
        override fun process(handle: Long,samples: FloatArray,count: Int,rate: Int): Int { processes++;onProcess();return 1 }
        override fun destroy(handle: Long) { assertEquals(7L,handle);destroys++ }
    }
    private fun rejects(action: ()->Unit) { try { action();fail("Accepted invalid lease") } catch (_: Exception) {} }

    private class CaptureSession : AutoCloseable {
        val captureWorker=java.util.concurrent.Executors.newSingleThreadExecutor { Thread(it,"eilo-test-capture") }
        val inferenceWorker=java.util.concurrent.Executors.newSingleThreadExecutor { Thread(it,"eilo-test-inference") }
        val feed=java.util.concurrent.atomic.AtomicBoolean(false)
        val deviceClosed=java.util.concurrent.atomic.AtomicBoolean(false)
        val capture=ForegroundCapture(captureWorker,{true},{ object : CaptureDevice {
            override fun start() {}
            override fun read(samples: ShortArray): Int { if(!feed.get())return 0;samples[0]=100;return 1 }
            override fun close() { deviceClosed.set(true) }
        } })
        val controller=testController(effects=capture)
        init { controller.dispatch(ControllerEvent.START);await { controller.state()==ControllerState.STANDBY } }
        fun ticket()=capture.prepareWakeSetup(controller,controller.token()!!)!!
        fun install(ticket: ForegroundCapture.WakeSetupTicket,f: Fixture,api: NativeWakeAPI=NativeWakeAPI.unavailable) =
            inferenceWorker.submit<Boolean> { WakeCaptureInstaller.install(ticket,f.store,f.selection,WakeConfiguration("HEY EILO",.125f,1.5f),api) }
        fun await(check: ()->Boolean) {
            val end=System.nanoTime()+java.util.concurrent.TimeUnit.SECONDS.toNanos(5)
            while(!check() && System.nanoTime()<end)Thread.sleep(1)
            assertTrue(check())
        }
        override fun close() {
            controller.stop();captureWorker.shutdownNow();inferenceWorker.shutdownNow()
            assertTrue(captureWorker.awaitTermination(5,java.util.concurrent.TimeUnit.SECONDS))
            assertTrue(inferenceWorker.awaitTermination(5,java.util.concurrent.TimeUnit.SECONDS))
        }
    }
    @Test fun verifiedWorkerInstallationFeedsActualCaptureAndReleasesOwnedStream() {
        Fixture().use { f -> CaptureSession().use { c ->
            f.activate();val api=API { assertEquals("eilo-test-inference",Thread.currentThread().name) }
            assertTrue(c.install(c.ticket(),f,api).get(5,java.util.concurrent.TimeUnit.SECONDS))
            assertNull(c.capture.prepareWakeSetup(c.controller,c.controller.token()!!))
            c.feed.set(true);c.await { c.controller.state()==ControllerState.CAPTURING };c.await { api.destroys==1 }
            assertEquals(1,api.creates);assertTrue(api.processes>0);c.controller.stop();assertTrue(c.deviceClosed.get())
        } }
    }
    @Test fun contextClearBeforeQueuedSetupRejectsTicketButFreshTicketCanAttach() {
        Fixture().use { f -> CaptureSession().use { c ->
            f.activate();val ticket=c.ticket();val api=API();c.capture.clearVolatileContext()
            assertFalse(c.install(ticket,f,api).get(5,java.util.concurrent.TimeUnit.SECONDS));assertEquals(0,api.creates)
            assertFalse(c.deviceClosed.get());assertTrue(c.install(c.ticket(),f,api).get(5,java.util.concurrent.TimeUnit.SECONDS))
            c.controller.stop();assertEquals(1,api.destroys)
        } }
    }
    @Test fun stopOrClearDuringWorkerOpeningRejectsLateAttachmentAndClosesHandle() {
        for(stop in listOf(false,true)) Fixture().use { f -> CaptureSession().use { c ->
            f.activate();val entered=java.util.concurrent.CountDownLatch(1);val release=java.util.concurrent.CountDownLatch(1)
            val api=API { entered.countDown();check(release.await(5,java.util.concurrent.TimeUnit.SECONDS)) }
            val pending=c.install(c.ticket(),f,api)
            try {
                assertTrue(entered.await(5,java.util.concurrent.TimeUnit.SECONDS))
                if(stop)c.controller.stop() else c.capture.clearVolatileContext()
                release.countDown();assertFalse(pending.get(5,java.util.concurrent.TimeUnit.SECONDS));assertEquals(1,api.destroys)
                assertEquals(if(stop)ControllerState.STOPPED else ControllerState.STANDBY,c.controller.state())
                if(!stop) { val fresh=API();assertTrue(c.install(c.ticket(),f,fresh).get(5,java.util.concurrent.TimeUnit.SECONDS));c.controller.stop();assertEquals(1,fresh.destroys) }
            } finally { release.countDown() }
        } }
    }
    @Test fun unavailableRuntimeMissingOrCorruptPackNeverAttaches() {
        Fixture().use { f -> CaptureSession().use { c ->
            val api=API();assertFalse(c.install(c.ticket(),f,api).get(5,java.util.concurrent.TimeUnit.SECONDS));assertEquals(0,api.creates)
            f.activate();assertFalse(c.install(c.ticket(),f).get(5,java.util.concurrent.TimeUnit.SECONDS))
            assertNotNull(c.capture.prepareWakeSetup(c.controller,c.controller.token()!!))
            val p=f.store.active()!!;f.store.file(p,0).writeBytes(byteArrayOf(9,9,9,9))
            assertFalse(c.install(c.ticket(),f,api).get(5,java.util.concurrent.TimeUnit.SECONDS));assertEquals(0,api.creates)
            assertEquals(ControllerState.STANDBY,c.controller.state())
        } }
    }
    @Test fun signedStoreResolvesExactIdsAndUnavailableDefaultNeverGrantsReadiness() {
        Fixture().use { f ->
            f.activate();val lease=WakePackLease.resolve(f.store,f.selection)
            rejects { lease.openStream(configuration) }
            val api=API();val stream=lease.openStream(configuration,api)
            assertEquals(listOf("encoder.onnx","decoder.onnx","joiner.onnx","tokens.txt"),api.paths!!.let { listOf(it.encoder,it.decoder,it.joiner,it.tokens).map { p -> File(p).name } })
            stream.accept(floatArrayOf(0.5f),1,16000);assertEquals("HEY EILO",stream.keyword())
            stream.close();stream.close();assertEquals(1,api.destroys)
            lease.close();assertFalse(lease.verified());rejects { lease.openStream(configuration,api) };assertEquals(1,api.creates)
        }
    }
    @Test fun rejectsMissingMismatchedOrWrongRoleSelection() {
        Fixture().use { f ->
            rejects { WakePackLease.resolve(f.store,f.selection) };f.activate()
            for(selection in listOf(f.selection.copy(packId="other"),f.selection.copy(runtimeRevision="d".repeat(40)),f.selection.copy(encoder=WakeArtifactPin("encoder","d".repeat(64))),f.selection.copy(joiner=WakeArtifactPin("absent",f.pins[2].sha256)))) {
                rejects { WakePackLease.resolve(f.store,selection) }
            }
            rejects { f.selection.copy(tokens=f.selection.encoder) }
            rejects { WakeArtifactPin("../encoder",f.pins[0].sha256) }
            f.activate(f.pack(2,wrongRole=true));rejects { WakePackLease.resolve(f.store,f.selection) }
            f.activate(f.pack(3,omit=true));rejects { WakePackLease.resolve(f.store,f.selection) }
        }
    }
    @Test fun replacementAndFailedActivationRevokeExistingBorrowWithoutRehashing() {
        Fixture().use { f ->
            f.activate();val lease=WakePackLease.resolve(f.store,f.selection);val api=API();val stream=lease.openStream(configuration,api)
            f.activate(f.pack(2));assertFalse(lease.verified())
            rejects { stream.accept(floatArrayOf(0.5f),1,16000) };assertEquals(0,api.processes);assertEquals(1,api.destroys)
            val next=WakePackLease.resolve(f.store,f.selection)
            // Even a rejected rollback invalidates all outstanding store leases conservatively.
            rejects { f.activate(f.pack(1)) };assertFalse(next.verified())
        }
    }
    @Test fun replacementDuringOpeningDestroysUnpublishedHandle() {
        Fixture().use { f ->
            f.activate();val lease=WakePackLease.resolve(f.store,f.selection)
            val api=API { f.activate(f.pack(2)) }
            rejects { lease.openStream(configuration,api) };assertEquals(1,api.creates);assertEquals(1,api.destroys);assertEquals(0,api.processes)
        }
    }
    @Test fun revocationDuringDecodeRejectsKeywordAndDestroysHandle() {
        Fixture().use { f ->
            f.activate();val lease=WakePackLease.resolve(f.store,f.selection);val api=API()
            val stream=lease.openStream(configuration,api);api.onProcess={ lease.close() }
            rejects { stream.accept(floatArrayOf(0.5f),1,16000) }
            assertEquals(1,api.processes);assertEquals(1,api.destroys)
            rejects { stream.keyword() };stream.close();assertEquals(1,api.destroys)
        }
    }
    @Test fun signedPackReplacementAfterQueueDrainRejectsPendingActivation() {
        Fixture().use { f ->
            f.activate();val lease=WakePackLease.resolve(f.store,f.selection);val api=API()
            val c=testController();c.dispatch(ControllerEvent.START);val token=c.token()!!
            val detector=WakeDetector(configuration,verified=lease::verified,open={ lease.openStream(it,api) })
            val delivery=WakeFrameDelivery(16000,detector,token)
            assertTrue(delivery.submit(shortArrayOf(100),1,16000))
            val event=(delivery.drain() as WakeDrain.Events).values.single()
            f.activate(f.pack(2));assertFalse(event.apply(c));assertEquals(ControllerState.STANDBY,c.state())
            assertFalse(detector.isActive(token));assertFalse(event.apply(c))
            delivery.close();lease.close();assertEquals(1,api.destroys);c.stop()
        }
    }
    @Test fun corruptFileOrSymlinkCannotProduceLeaseAndExplicitRevocationRejectsResult() {
        Fixture().use { f ->
            f.activate();val pack=f.store.active()!!;val target=f.store.file(pack,pack.manifest.artifacts.indexOfFirst { it.id=="encoder" })
            val lease=WakePackLease.resolve(f.store,f.selection);val api=API();val stream=lease.openStream(configuration,api)
            lease.close();rejects { stream.keyword() };assertEquals(1,api.destroys)
            target.writeBytes(byteArrayOf(9,9,9,9));rejects { WakePackLease.resolve(f.store,f.selection) }
            target.delete();Files.createSymbolicLink(target.toPath(),f.source[0].toPath());rejects { WakePackLease.resolve(f.store,f.selection) }
        }
    }
}
