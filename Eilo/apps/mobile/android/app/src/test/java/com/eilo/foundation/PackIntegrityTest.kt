package com.eilo.foundation
import org.junit.Assert.*
import org.junit.Test
import java.nio.file.Files
class PackIntegrityTest {
 @Test fun exactPassesCorruptPartialAndSymlinkFail() {
  val root=Files.createTempDirectory("eilo-pack").toFile();val f=java.io.File(root,"part");val pack=PackFixtures.verified()
  try {
   f.writeBytes(byteArrayOf(1,2,3,4));assertEquals(pack.digest,VerifiedArtifact.verify(pack,0,f).packDigest)
   for(bytes in listOf(byteArrayOf(1,2),byteArrayOf(1,2,3,5),byteArrayOf(1,2,3,4,5))) { f.writeBytes(bytes);try { VerifiedArtifact.verify(pack,0,f);fail() } catch (_: Exception) {} }
   f.writeBytes(byteArrayOf(1,2,3,4));val link=java.io.File(root,"link");Files.createSymbolicLink(link.toPath(),f.toPath());try { VerifiedArtifact.verify(pack,0,link);fail() } catch (_: Exception) {}
  } finally { root.deleteRecursively() }
 }
 @Test fun cancellationCannotIssueProof() {
  val c=PackCancellation();c.cancel();try { VerifiedArtifact.verify(PackFixtures.verified(),0,java.io.File("missing"),c);fail() } catch (_: Exception) {}
 }
}
