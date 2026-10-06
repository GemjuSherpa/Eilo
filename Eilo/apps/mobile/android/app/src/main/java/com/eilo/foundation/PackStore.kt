package com.eilo.foundation
import java.io.File
import java.nio.file.Files
import java.nio.file.StandardCopyOption
import java.nio.file.StandardOpenOption
import java.nio.channels.FileChannel
import java.util.UUID

enum class PackActivationStep { COPIED, VERIFIED, BEFORE_POINTER, AFTER_POINTER }
/** App-private, no-backup root; caller uses installer worker. All store operations serialize. */
class PackStore(private val root: File, trust: Map<String,ByteArray>, private val runtime: String, private val licenseEvidence: Set<String> = emptySet(),private val android: Int=35) {
 companion object { private val storeLock=Any();private val storeEpoch=java.util.concurrent.atomic.AtomicReference(UUID.randomUUID()) }
 fun epoch(): UUID=storeEpoch.get()
 private fun <T> locked(operation: ()->T): T = synchronized(storeLock) { operation() }
 private val trust=trust.mapValues { it.value.clone() }
 private fun verify(payload: ByteArray,signature: ByteArray,key: String)=VerifiedPack.verify(payload,signature,key,"ES256",trust,runtime,android)
 private fun directories(): Pair<File,File> { val r=PackFiles.directory(root);return r to PackFiles.directory(PackFiles.child(r,"versions")) }
 private fun readSlot(slot: File): VerifiedPack {
  val payload=PackFiles.child(slot,".manifest");val signature=PackFiles.child(slot,".signature");val key=PackFiles.child(slot,".key")
  check(payload.length() in 1..65536 && signature.length() in 8..72 && key.length() in 1..64)
  val p=verify(payload.readBytes(),signature.readBytes(),key.readText());check(slot.name==p.digest)
  check(p.manifest.artifacts.all { it.licenseEvidence in licenseEvidence }) { "license" }
  p.manifest.artifacts.indices.forEach { VerifiedArtifact.verify(p,it,PackFiles.child(slot,p.manifest.artifacts[it].filename)) }
  return p
 }
 fun active(): VerifiedPack? = locked {
  val (r,versions)=directories();val pointer=PackFiles.child(r,".active");if(!pointer.exists())return@locked null
  check(pointer.length()==64L);val digest=pointer.readText();check(digest.matches(Regex("[a-f0-9]{64}")))
  return@locked readSlot(PackFiles.child(versions,digest))
 }
 fun file(pack: VerifiedPack,index: Int): File = locked {
  val current=active() ?: error("unavailable");check(current.digest==pack.digest)
  val (_,versions)=directories();return@locked PackFiles.child(PackFiles.child(versions,current.digest),current.manifest.artifacts[index].filename)
 }
 fun activate(pack: VerifiedPack,proofs: List<VerifiedArtifact>,cancel: PackCancellation,step: (PackActivationStep)->Unit={}) = locked {
  storeEpoch.set(UUID.randomUUID())
  val checked=verify(pack.signedPayload(),pack.signatureBytes(),pack.keyId)
  check(checked.manifest.artifacts.all { it.licenseEvidence in licenseEvidence }) { "license" }
  val (r,versions)=directories();val old=active()
  if(old!=null) check(checked.manifest.packId==old.manifest.packId && (checked.manifest.revision>old.manifest.revision || checked.digest==old.digest)) { "rollback" }
  check(proofs.size==checked.manifest.artifacts.size && proofs.map { it.index }.toSet()==checked.manifest.artifacts.indices.toSet() && proofs.all { it.packDigest==checked.digest })
  val slot=PackFiles.child(versions,checked.digest)
  if(slot.exists()) { check(readSlot(slot).digest==checked.digest) }
  else {
   check(r.usableSpace>checked.manifest.artifacts.sumOf { it.bytes }+1_000_000L)
   val pending=PackFiles.directory(PackFiles.child(versions,"pending-"+UUID.randomUUID()))
   try {
    for(proof in proofs) {
     cancel.check();VerifiedArtifact.verify(checked,proof.index,proof.file,cancel)
     val destination=PackFiles.child(pending,checked.manifest.artifacts[proof.index].filename)
     Files.copy(proof.file.toPath(),destination.toPath());java.io.FileOutputStream(destination,true).use { it.fd.sync() }
    }
    PackFiles.atomic(PackFiles.child(pending,".manifest"),checked.signedPayload());PackFiles.atomic(PackFiles.child(pending,".signature"),checked.signatureBytes());PackFiles.atomic(PackFiles.child(pending,".key"),checked.keyId.toByteArray())
    step(PackActivationStep.COPIED);checked.manifest.artifacts.indices.forEach { VerifiedArtifact.verify(checked,it,PackFiles.child(pending,checked.manifest.artifacts[it].filename),cancel) }
    step(PackActivationStep.VERIFIED);syncDirectory(pending);cancel.check()
    Files.move(pending.toPath(),slot.toPath(),StandardCopyOption.ATOMIC_MOVE);syncDirectory(versions)
   } finally { if(pending.exists()) check(pending.deleteRecursively()) { "activation" } }
  }
  step(PackActivationStep.BEFORE_POINTER);cancel.check();PackFiles.atomic(PackFiles.child(r,".active"),checked.digest.toByteArray());syncDirectory(r);step(PackActivationStep.AFTER_POINTER)
 }
 private fun syncDirectory(dir: File) { FileChannel.open(dir.toPath(),StandardOpenOption.READ).use { it.force(true) } }
}
