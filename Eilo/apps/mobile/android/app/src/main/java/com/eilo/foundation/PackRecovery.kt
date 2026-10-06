package com.eilo.foundation
import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import org.json.JSONObject
internal object PackFiles {
 fun directory(dir: File): File { check(!Files.isSymbolicLink(dir.toPath()));Files.createDirectories(dir.toPath());check(Files.isDirectory(dir.toPath()));return dir.canonicalFile }
 fun child(root: File,name: String): File { require(name.matches(Regex("[a-zA-Z0-9._-]+")) && name!="." && name!="..");val f=File(root,name);check(!Files.isSymbolicLink(f.toPath()) && f.canonicalFile.parentFile==root.canonicalFile);return f }
 fun atomic(file: File,bytes: ByteArray) { val tmp=child(file.parentFile,file.name+".tmp");java.io.FileOutputStream(tmp).use { it.write(bytes);it.fd.sync() };Files.move(tmp.toPath(),file.toPath(),StandardCopyOption.ATOMIC_MOVE,StandardCopyOption.REPLACE_EXISTING) }
 fun remove(file: File) { Files.deleteIfExists(file.toPath()) }
}
class PackRecovery(private val transport: PackTransport) {
 /** Generic checkpoints bind a strong validator to exact signed manifest and artifact index. */
 fun download(pack: VerifiedPack,index: Int,staging: File,cancel: PackCancellation): VerifiedArtifact {
  val root=PackFiles.directory(staging);val a=pack.manifest.artifacts[index];val f=PackFiles.child(root,a.filename+".partial");val journal=PackFiles.child(root,a.filename+".resume")
  if(f.exists() && f.length()==a.bytes) {
   try { val proof=VerifiedArtifact.verify(pack,index,f,cancel);PackFiles.remove(journal);return proof }
   catch (e: Exception) { cancel.check();PackFiles.remove(f);PackFiles.remove(journal);throw e }
  }
  var etag: String?=null;var offset=0L
  if(f.exists() && journal.exists() && journal.length()<=1024) {
   try { val o=JSONObject(journal.readText());if(o.keys().asSequence().toSet()==setOf("digest","index","etag") && o.getString("digest")==pack.digest && o.getInt("index")==index && PackTransport.strongEtag(o.getString("etag")) && f.length() in 1 until a.bytes) { etag=o.getString("etag");offset=f.length() } } catch (_: Exception) { /* Invalid generic checkpoint is discarded below. */ }
  }
  fun reset() { PackFiles.remove(f);PackFiles.remove(journal) }
  if(offset==0L) reset()
  val save: (String?)->Unit={ validator ->
   cancel.check();if(validator==null) PackFiles.remove(journal)
   else PackFiles.atomic(journal,JSONObject().put("digest",pack.digest).put("index",index).put("etag",validator).toString().toByteArray())
  }
  try { transport.transfer(pack,index,f,cancel,offset,etag,save) }
  catch (_: PackRestartRequired) { cancel.check();reset();transport.transfer(pack,index,f,cancel,validator=save) }
  try { val proof=VerifiedArtifact.verify(pack,index,f,cancel);PackFiles.remove(journal);return proof }
  catch(e: Exception) { cancel.check();reset();throw e }
 }
}
