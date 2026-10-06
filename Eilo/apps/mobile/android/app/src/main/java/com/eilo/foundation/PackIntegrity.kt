package com.eilo.foundation
import java.io.File
import java.nio.file.Files
import java.nio.file.LinkOption
import java.nio.file.attribute.BasicFileAttributes
import java.security.MessageDigest
class VerifiedArtifact private constructor(val file: File,val packDigest: String,val index: Int) {
 companion object {
  fun verify(pack: VerifiedPack,index: Int,file: File,cancel: PackCancellation=PackCancellation()): VerifiedArtifact {
   val a=pack.manifest.artifacts[index];cancel.check()
   val attrs=Files.readAttributes(file.toPath(),BasicFileAttributes::class.java,LinkOption.NOFOLLOW_LINKS)
   check(attrs.isRegularFile && attrs.size()==a.bytes) { "integrity" }
   val digest=MessageDigest.getInstance("SHA-256");var count=0L
   Files.newInputStream(file.toPath(),LinkOption.NOFOLLOW_LINKS).use { input ->
    val buffer=ByteArray(65536);while(true) { cancel.check();val n=input.read(buffer);if(n<0)break;check(n.toLong()<=a.bytes-count);digest.update(buffer,0,n);count+=n }
   }
   val after=Files.readAttributes(file.toPath(),BasicFileAttributes::class.java,LinkOption.NOFOLLOW_LINKS)
   check(count==a.bytes && attrs.fileKey()==after.fileKey() && attrs.lastModifiedTime()==after.lastModifiedTime() && after.isRegularFile && after.size()==a.bytes) { "integrity" }
   val expected=a.sha256.chunked(2).map { it.toInt(16).toByte() }.toByteArray();check(MessageDigest.isEqual(digest.digest(),expected)) { "integrity" }
   return VerifiedArtifact(file,pack.digest,index)
  }
 }
}
