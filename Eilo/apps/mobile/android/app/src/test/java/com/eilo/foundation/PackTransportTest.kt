package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
import java.nio.file.Files
class FakePackServer(var headers: PackHeaders=PackHeaders(200,4,etag="\"one\""),var body: ByteArray=byteArrayOf(1,2,3,4)) : PackHTTPClient {
 val requests=mutableListOf<PackRequest>()
 override fun fetch(request: PackRequest,cancel: PackCancellation,response: (PackHeaders)->Unit,chunk: (ByteArray,Int)->Unit) { requests.add(request);response(headers);if(headers.status in 200..299) chunk(body,body.size) }
}
class PackTransportTest {
 @Test fun genericRequestAndBoundedWrite() {
  val root=Files.createTempDirectory("eilo-pack").toFile()
  try { val f=java.io.File(root,"partial");val server=FakePackServer();val t=PackTransport(PackOriginPolicy(setOf("https://models.example.test")),server)
   assertEquals("\"one\"",t.transfer(PackFixtures.verified(),0,f,PackCancellation()));assertArrayEquals(byteArrayOf(1,2,3,4),f.readBytes());assertEquals(PackRequest("https://models.example.test/model.gguf",0,null),server.requests.single())
  } finally { root.deleteRecursively() }
 }
 @Test fun foreignRedirectAndUnconfiguredOriginNeverRequested() {
  val root=Files.createTempDirectory("eilo-pack").toFile()
  try { val server=FakePackServer(PackHeaders(302,0,location="https://foreign.example.test/file"));val t=PackTransport(PackOriginPolicy(setOf("https://models.example.test")),server)
   try { t.transfer(PackFixtures.verified(),0,java.io.File(root,"part"),PackCancellation());fail() } catch (_: Exception) {}
   assertEquals(1,server.requests.size);assertFalse(java.io.File(root,"part").exists())
   val empty=FakePackServer();try { PackTransport(PackOriginPolicy(emptySet()),empty).transfer(PackFixtures.verified(),0,java.io.File(root,"part"),PackCancellation());fail() } catch (_: Exception) {};assertTrue(empty.requests.isEmpty())
  } finally { root.deleteRecursively() }
 }
 @Test fun cancellationLengthAndEncodingFailClosed() {
  val root=Files.createTempDirectory("eilo-pack").toFile()
  try { for(h in listOf(PackHeaders(200,5),PackHeaders(200,4,encoding="gzip"),PackHeaders(401,4))) {
   try { PackTransport(PackOriginPolicy(setOf("https://models.example.test")),FakePackServer(h)).transfer(PackFixtures.verified(),0,java.io.File(root,"part"),PackCancellation());fail() } catch (_: Exception) {};assertFalse(java.io.File(root,"part").exists())
  }
   val c=PackCancellation();c.cancel();val server=FakePackServer();try { PackTransport(PackOriginPolicy(setOf("https://models.example.test")),server).transfer(PackFixtures.verified(),0,java.io.File(root,"part"),c);fail() } catch (_: Exception) {};assertTrue(server.requests.isEmpty())
  } finally { root.deleteRecursively() }
 }
}
