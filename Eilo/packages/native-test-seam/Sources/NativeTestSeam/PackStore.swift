import Foundation
import Darwin
public enum PackActivationStep { case copied,verified,beforePointer,afterPointer }
/// App-private no-backup root, serialized installer-worker operations. No production trust/license approvals by default.
public final class PackStore {
  private let root: URL,trust: [String:Data],runtime: String,licenseEvidence: Set<String>,ios: Int
  private static let sharedLock=NSRecursiveLock()
  private var lock: NSRecursiveLock { Self.sharedLock }
  public init(root: URL,trust: [String:Data],runtime: String,licenseEvidence: Set<String>=[],ios: Int=18) { self.root=root;self.trust=trust;self.runtime=runtime;self.licenseEvidence=licenseEvidence;self.ios=ios }
  private func verify(_ payload: Data,_ signature: Data,_ key: String) throws -> VerifiedPack { try VerifiedPack.verify(payload:payload,signature:signature,keyID:key,algorithm:"ES256",trust:trust,runtime:runtime,ios:ios) }
  private func directories() throws -> (URL,URL) { let r=try PackFiles.directory(root);return (r,try PackFiles.directory(PackFiles.child(r,"versions"))) }
  private func readSlot(_ slot: URL) throws -> VerifiedPack {
    let payload=try PackFiles.child(slot,".manifest"),signature=try PackFiles.child(slot,".signature"),key=try PackFiles.child(slot,".key")
    func size(_ u: URL) throws -> Int { try u.resourceValues(forKeys:[.fileSizeKey]).fileSize ?? 0 }
    guard (1...65536).contains(try size(payload)),(8...72).contains(try size(signature)),(1...64).contains(try size(key)) else { throw PackFailure.activation }
    let p=try verify(Data(contentsOf:payload),Data(contentsOf:signature),String(contentsOf:key,encoding:.utf8))
    guard slot.lastPathComponent==p.digest,p.manifest.artifacts.allSatisfy({ licenseEvidence.contains($0.licenseEvidence) }) else { throw PackFailure.activation }
    for i in p.manifest.artifacts.indices { _=try VerifiedArtifact.verify(p,index:i,file:PackFiles.child(slot,p.manifest.artifacts[i].filename)) };return p
  }
  public func active() throws -> VerifiedPack? {
    lock.lock();defer { lock.unlock() };let (r,versions)=try directories(),pointer=try PackFiles.child(r,".active")
    guard FileManager.default.fileExists(atPath:pointer.path) else { return nil }
    guard try pointer.resourceValues(forKeys:[.fileSizeKey]).fileSize==64 else { throw PackFailure.activation }
    let digest=try String(contentsOf:pointer,encoding:.utf8);guard digest.range(of:"^[a-f0-9]{64}$",options:.regularExpression) != nil else { throw PackFailure.activation }
    return try readSlot(PackFiles.child(versions,digest))
  }
  public func file(_ pack: VerifiedPack,index: Int) throws -> URL {
    lock.lock();defer { lock.unlock() };guard let current=try active(),current.digest==pack.digest,current.manifest.artifacts.indices.contains(index) else { throw PackFailure.unavailable }
    let (_,versions)=try directories();return try PackFiles.child(PackFiles.child(versions,current.digest),current.manifest.artifacts[index].filename)
  }
  public func activate(_ pack: VerifiedPack,proofs: [VerifiedArtifact],cancel: PackCancellation,step: (PackActivationStep)throws->Void = { _ in }) throws {
    lock.lock();defer { lock.unlock() };let checked=try verify(pack.signedPayload,pack.signatureBytes,pack.keyID)
    guard checked.manifest.artifacts.allSatisfy({ licenseEvidence.contains($0.licenseEvidence) }) else { throw PackFailure.activation }
    let (r,versions)=try directories(),old=try active()
    if let old=old { guard checked.manifest.packID==old.manifest.packID && (checked.manifest.revision>old.manifest.revision || checked.digest==old.digest) else { throw PackFailure.activation } }
    guard proofs.count==checked.manifest.artifacts.count,Set(proofs.map(\.index))==Set(checked.manifest.artifacts.indices),proofs.allSatisfy({ $0.packDigest==checked.digest }) else { throw PackFailure.activation }
    let slot=try PackFiles.child(versions,checked.digest)
    if FileManager.default.fileExists(atPath:slot.path) { guard try readSlot(slot).digest==checked.digest else { throw PackFailure.activation } }
    else {
      let free=(try FileManager.default.attributesOfFileSystem(forPath:r.path)[.systemFreeSize] as? NSNumber)?.int64Value ?? 0
      guard free>checked.manifest.artifacts.reduce(Int64(1_000_000), { $0+$1.bytes }) else { throw PackFailure.activation }
      let pending=try PackFiles.directory(PackFiles.child(versions,"pending-"+UUID().uuidString))
      defer { if FileManager.default.fileExists(atPath:pending.path) { try? FileManager.default.removeItem(at:pending) } }
      for proof in proofs {
        try cancel.check();_=try VerifiedArtifact.verify(checked,index:proof.index,file:proof.file,cancel:cancel)
        let dest=try PackFiles.child(pending,checked.manifest.artifacts[proof.index].filename);try FileManager.default.copyItem(at:proof.file,to:dest)
        let h=try FileHandle(forWritingTo:dest);try h.synchronize();try h.close()
      }
      try PackFiles.atomic(PackFiles.child(pending,".manifest"),checked.signedPayload);try PackFiles.atomic(PackFiles.child(pending,".signature"),checked.signatureBytes);try PackFiles.atomic(PackFiles.child(pending,".key"),Data(checked.keyID.utf8))
      try step(.copied);for i in checked.manifest.artifacts.indices { _=try VerifiedArtifact.verify(checked,index:i,file:PackFiles.child(pending,checked.manifest.artifacts[i].filename),cancel:cancel) }
      try step(.verified);try syncDirectory(pending);try cancel.check()
      guard rename(pending.path,slot.path)==0 else { throw PackFailure.activation };try syncDirectory(versions)
    }
    try step(.beforePointer);try cancel.check();try PackFiles.atomic(PackFiles.child(r,".active"),Data(checked.digest.utf8));try syncDirectory(r);try step(.afterPointer)
  }
  private func syncDirectory(_ dir: URL) throws { let fd=open(dir.path,O_RDONLY|O_DIRECTORY);guard fd>=0 else { throw PackFailure.activation };defer { close(fd) };guard fsync(fd)==0 else { throw PackFailure.activation } }
}
