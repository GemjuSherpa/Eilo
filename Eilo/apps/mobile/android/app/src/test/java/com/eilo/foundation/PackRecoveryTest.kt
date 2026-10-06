package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
import java.nio.file.Files
class InterruptedPackServer : PackHTTPClient {
 var mode=0;val offsets=mutableListOf<Long>()
 override fun fetch(request: PackRequest,cancel: PackCancellation,response: (PackHeaders)->Unit,chunk: (ByteArray,Int)->Unit) {
  offsets.add(request.offset)
  if(mode==0) { response(PackHeaders(200,4,etag="\"one\""));chunk(byteArrayOf(1,2),2);throw java.io.IOException("synthetic") }
  if(request.offset==2L) { response(PackHeaders(206,2,etag=if(mode==2)"\"two\"" else "\"one\"",range="bytes 2-3/4"));chunk(byteArrayOf(3,4),2) }
  else { response(PackHeaders(200,4,etag="\"two\""));chunk(byteArrayOf(1,2,3,4),4) }
 }
}
class PackRecoveryTest {
 @Test fun interruptionResumesAndReverifiesWholeFile() {
  val root=Files.createTempDirectory("eilo-pack").toFile();val server=InterruptedPackServer();val r=PackRecovery(PackTransport(PackOriginPolicy(setOf("https://models.example.test")),server));val p=PackFixtures.verified()
  try { try { r.download(p,0,root,PackCancellation());fail() } catch (_: Exception) {};assertEquals(2L,java.io.File(root,"model.gguf.partial").length());server.mode=1
   val proof=r.download(p,0,root,PackCancellation());assertArrayEquals(byteArrayOf(1,2,3,4),proof.file.readBytes());assertEquals(listOf(0L,2L),server.offsets)
  } finally { root.deleteRecursively() }
 }
 @Test fun changedEtagRestartsAndInvalidJournalCannotResume() {
  for(tamper in listOf(false,true)) {
   val root=Files.createTempDirectory("eilo-pack").toFile();val server=InterruptedPackServer();val r=PackRecovery(PackTransport(PackOriginPolicy(setOf("https://models.example.test")),server));val p=PackFixtures.verified()
   try { try { r.download(p,0,root,PackCancellation());fail() } catch (_: Exception) {};server.mode=2
    if(tamper)java.io.File(root,"model.gguf.resume").writeText("{}")
    assertArrayEquals(byteArrayOf(1,2,3,4),r.download(p,0,root,PackCancellation()).file.readBytes());assertEquals(if(tamper)listOf(0L,0L) else listOf(0L,2L,0L),server.offsets)
   } finally { root.deleteRecursively() }
  }
 }
}
