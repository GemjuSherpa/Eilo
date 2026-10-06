package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
import java.nio.file.Files
import java.security.KeyPairGenerator
import java.security.Signature
import java.security.spec.ECGenParameterSpec
class PackStoreTest {
 @Test fun failuresKeepOldVersionAndCommitHasNoMixedFiles() {
  val root=Files.createTempDirectory("eilo-pack").toFile();val gen=KeyPairGenerator.getInstance("EC");gen.initialize(ECGenParameterSpec("secp256r1"));val key=gen.generateKeyPair();val trust=mapOf("test-key" to key.public.encoded)
  fun pack(revision: Int): VerifiedPack { val bytes=String(PackFixtures.payload).replace("\"revision\":1","\"revision\":$revision").toByteArray();val sig=Signature.getInstance("SHA256withECDSA");sig.initSign(key.private);sig.update(bytes);return VerifiedPack.verify(bytes,sig.sign(),"test-key","ES256",trust,PackFixtures.runtime) }
  try {
   val store=PackStore(java.io.File(root,"store"),trust,PackFixtures.runtime,setOf("c".repeat(64)));val file=java.io.File(root,"model");file.writeBytes(byteArrayOf(1,2,3,4));val first=pack(1);store.activate(first,listOf(VerifiedArtifact.verify(first,0,file)),PackCancellation());assertEquals(first.digest,store.active()!!.digest)
   for((index,boundary) in listOf(PackActivationStep.COPIED,PackActivationStep.VERIFIED,PackActivationStep.BEFORE_POINTER).withIndex()) {
    val next=pack(index+2);try { store.activate(next,listOf(VerifiedArtifact.verify(next,0,file)),PackCancellation()) { if(it==boundary)error("synthetic crash") };fail() } catch (_: Exception) {};assertEquals(first.digest,store.active()!!.digest)
   }
   val next=pack(5);try { store.activate(next,listOf(VerifiedArtifact.verify(next,0,file)),PackCancellation()) { if(it==PackActivationStep.AFTER_POINTER)error("synthetic crash") } } catch (_: Exception) {}
   assertEquals(next.digest,PackStore(java.io.File(root,"store"),trust,PackFixtures.runtime,setOf("c".repeat(64))).active()!!.digest)
   try { store.activate(first,listOf(VerifiedArtifact.verify(first,0,file)),PackCancellation());fail() } catch (_: Exception) {};assertEquals(next.digest,store.active()!!.digest)
   store.file(next,0).writeBytes(byteArrayOf(1,2,3,5));try { store.active();fail() } catch (_: Exception) {}
  } finally { root.deleteRecursively() }
 }
 @Test fun staleProofMissingLicenseAndEmptyTrustCannotActivate() {
  val root=Files.createTempDirectory("eilo-pack").toFile();val (p,trust)=PackFixtures.signed();val f=java.io.File(root,"part");f.writeBytes(byteArrayOf(1,2,3,4));val proof=VerifiedArtifact.verify(p,0,f)
  try {
   for(t in listOf(trust,emptyMap())) { val s=PackStore(java.io.File(root,"store"),t,PackFixtures.runtime);try { s.activate(p,listOf(proof),PackCancellation());fail() } catch (_: Exception) {} }
   val s=PackStore(java.io.File(root,"store"),trust,PackFixtures.runtime,setOf("c".repeat(64)));f.writeBytes(byteArrayOf(9,9,9,9));try { s.activate(p,listOf(proof),PackCancellation());fail() } catch (_: Exception) {};assertNull(s.active())
  } finally { root.deleteRecursively() }
 }
}
