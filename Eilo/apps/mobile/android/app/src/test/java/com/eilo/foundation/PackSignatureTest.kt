package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
import java.security.KeyPairGenerator
import java.security.Signature
import java.security.spec.ECGenParameterSpec
class PackSignatureTest {
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
