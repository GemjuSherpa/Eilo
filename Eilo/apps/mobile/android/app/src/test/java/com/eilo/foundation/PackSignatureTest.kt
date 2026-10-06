package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
import java.security.KeyPairGenerator
import java.security.Signature
import java.security.spec.ECGenParameterSpec
class PackSignatureTest {
 @Test fun sharedOpenSslVectorVerifiesExactWireFormat() {
  fun bytes(hex: String)=hex.chunked(2).map { it.toInt(16).toByte() }.toByteArray()
  val p=VerifiedPack.verify(PackFixtures.payload,bytes("3045022100cd5d8c97ac16144866d24c916c864634f8ed756695e3236e9463c3a8e705953c0220687f9989ae1a385c631b164e887a53f6c795bcea0322e12531d767dd8e6634dd"),"vector","ES256",mapOf("vector" to bytes("3059301306072a8648ce3d020106082a8648ce3d03010703420004d2e47e7184a3b316ff8701e945c498cebf4796c71143854cb09113dbc38e2e957f86f44fb89059a3693aaf38dcfb6681e5d6f5645b3e28cc5700ae4b24d838ca")),PackFixtures.runtime)
  assertEquals("test-pack",p.manifest.packId)
 }
 @Test fun authenticatesExactBytesAndRejectsUnknownTrust() {
  val gen=KeyPairGenerator.getInstance("EC");gen.initialize(ECGenParameterSpec("secp256r1"));val pair=gen.generateKeyPair()
  val p=PackFixtures.payload.clone();val signer=Signature.getInstance("SHA256withECDSA");signer.initSign(pair.private);signer.update(p);val s=signer.sign();val trust=mapOf("test-key" to pair.public.encoded)
  val verified=VerifiedPack.verify(p,s,"test-key","ES256",trust,PackFixtures.runtime);assertEquals("test-pack",verified.manifest.packId)
  p[0]=0;assertEquals('{'.code.toByte(),verified.signedPayload()[0])
  for ((payload,key,algorithm,sig) in listOf(listOf(p,"test-key","ES256",s),listOf(PackFixtures.payload,"unknown","ES256",s),listOf(PackFixtures.payload,"test-key","none",s),listOf(PackFixtures.payload,"test-key","ES256",ByteArray(64)))) {
   try { VerifiedPack.verify(payload as ByteArray,sig as ByteArray,key as String,algorithm as String,trust,PackFixtures.runtime);fail() } catch (_: Exception) {}
  }
  try { VerifiedPack.verify(PackFixtures.payload,s,"test-key","ES256",emptyMap(),PackFixtures.runtime);fail() } catch (_: Exception) {}
 }
}
