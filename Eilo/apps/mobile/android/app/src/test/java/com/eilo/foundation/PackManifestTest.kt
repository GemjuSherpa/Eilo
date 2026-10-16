package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
object PackFixtures { val runtime="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"; fun verified(bytes: ByteArray=payload): VerifiedPack = signed(bytes).first
 fun signed(bytes: ByteArray=payload): Pair<VerifiedPack,Map<String,ByteArray>> { val g=java.security.KeyPairGenerator.getInstance("EC");g.initialize(java.security.spec.ECGenParameterSpec("secp256r1"));val k=g.generateKeyPair();val v=java.security.Signature.getInstance("SHA256withECDSA");v.initSign(k.private);v.update(bytes);val trust=mapOf("test-key" to k.public.encoded);return VerifiedPack.verify(bytes,v.sign(),"test-key","ES256",trust,runtime) to trust }; val payload="""{"schema":1,"packId":"test-pack","revision":1,"runtimeRevision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","minAndroid":35,"minIos":18,"artifacts":[{"id":"llm","filename":"model.gguf","role":"llm","url":"https://models.example.test/model.gguf","sha256":"9f64a747e1b97f131fabb6b447296c9b6f0201e79fb3c5356e6c77e89b6a806a","bytes":4,"license":"Apache-2.0","licenseEvidence":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}]}""".toByteArray() }
class PackManifestTest {
 @Test fun verifiedManifestCannotBeMutated() { val p=PackFixtures.verified();try { (p.manifest.artifacts as MutableList).clear();fail() } catch (_: UnsupportedOperationException) {};assertEquals(1,p.manifest.artifacts.size) }
 @Test fun validMetadata() { val m=PackManifest.parse(PackFixtures.payload,PackFixtures.runtime);assertEquals(4L,m.artifacts.single().bytes) }
 @Test fun rejectsUnsafeAndIncomplete() {
  val s=String(PackFixtures.payload)
  val bad=listOf(s.replace("model.gguf","../model.gguf"),s.replace("https://","http://"),s.replace("Apache-2.0","unknown"),s.replace("\"schema\":1","\"schema\":2"),s.replace("\"bytes\":4","\"bytes\":4.0"),s.replace("\"revision\":1","\"revision\":1,\"revision\":2"),s.replace("\"packId\"","\"unexpected\""),s.replace("model.gguf\"","model.gguf?tracking=1\""))
  bad.forEach { try { PackManifest.parse(it.toByteArray(),PackFixtures.runtime);fail("Accepted invalid manifest") } catch (_: Exception) {} }
 }
 @Test fun rejectsRuntimePlatformAndBounds() {
  for (p in listOf(PackFixtures.payload,ByteArray(65537))) { try { PackManifest.parse(p,"d".repeat(40));fail() } catch (_: Exception) {} }
  try { PackManifest.parse(PackFixtures.payload,PackFixtures.runtime,34);fail() } catch (_: Exception) {}
 }
 @Test fun onlyReviewedSpeechFilenamesAndRolesAreAdded() {
  fun payload(name:String,role:String):ByteArray {val root=org.json.JSONObject(String(PackFixtures.payload));root.getJSONArray("artifacts").getJSONObject(0).put("filename",name).put("role",role);return root.toString().toByteArray()}
  for(name in listOf("adapter.ort","cross_kv.ort","decoder_kv.ort","encoder.ort","frontend.model.ort","frontend.weights.ort")) {
   assertEquals(name,PackManifest.parse(payload(name,"asr"),PackFixtures.runtime).artifacts[0].filename)
   assertThrows(IllegalArgumentException::class.java){PackManifest.parse(payload(name,"vad"),PackFixtures.runtime)}
  }
  PackManifest.parse(payload("tokenizer.bin","tokenizer"),PackFixtures.runtime)
  for((name,role) in listOf("other.ort" to "asr","other.bin" to "tokenizer","tokenizer.bin" to "asr","../encoder.ort" to "asr","frontend.other.ort" to "asr","encoder.ort/child" to "asr"))assertThrows(IllegalArgumentException::class.java){PackManifest.parse(payload(name,role),PackFixtures.runtime)}
 }
}
