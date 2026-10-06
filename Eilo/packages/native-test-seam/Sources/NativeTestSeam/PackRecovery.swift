import Foundation
internal enum PackFiles {
  static func directory(_ dir: URL) throws -> URL {
    if (try? FileManager.default.destinationOfSymbolicLink(atPath:dir.path)) != nil { throw PackFailure.activation }
    if FileManager.default.fileExists(atPath:dir.path) { guard try dir.resourceValues(forKeys:[.isSymbolicLinkKey]).isSymbolicLink != true else { throw PackFailure.activation } }
    try FileManager.default.createDirectory(at:dir,withIntermediateDirectories:true)
    let root=dir.resolvingSymlinksInPath();guard try root.resourceValues(forKeys:[.isDirectoryKey]).isDirectory==true else { throw PackFailure.activation };return root
  }
  static func child(_ root: URL,_ name: String) throws -> URL {
    guard name.range(of:"^[a-zA-Z0-9._-]+$",options:.regularExpression) != nil,name != ".",name != ".." else { throw PackFailure.activation }
    let f=root.appendingPathComponent(name)
    if (try? FileManager.default.destinationOfSymbolicLink(atPath:f.path)) != nil { throw PackFailure.activation }
    if FileManager.default.fileExists(atPath:f.path) { guard try f.resourceValues(forKeys:[.isSymbolicLinkKey]).isSymbolicLink != true else { throw PackFailure.activation } }
    guard f.resolvingSymlinksInPath().deletingLastPathComponent()==root.resolvingSymlinksInPath() else { throw PackFailure.activation };return f
  }
  static func atomic(_ file: URL,_ bytes: Data) throws { try bytes.write(to:file,options:.atomic);let h=try FileHandle(forWritingTo:file);defer { try? h.close() };try h.synchronize() }
  static func remove(_ file: URL) throws { if FileManager.default.fileExists(atPath:file.path) { try FileManager.default.removeItem(at:file) } }
}
public final class PackRecovery {
  private let transport: PackTransport
  public init(transport: PackTransport) { self.transport=transport }
  public func download(_ pack: VerifiedPack,index: Int,staging: URL,cancel: PackCancellation) throws -> VerifiedArtifact {
    guard pack.manifest.artifacts.indices.contains(index) else { throw PackFailure.manifest }
    let root=try PackFiles.directory(staging),a=pack.manifest.artifacts[index],f=try PackFiles.child(root,a.filename+".partial"),journal=try PackFiles.child(root,a.filename+".resume")
    func size(_ file: URL) -> Int64 { (try? FileManager.default.attributesOfItem(atPath:file.path)[.size] as? Int64) ?? 0 }
    func reset() throws { try PackFiles.remove(f);try PackFiles.remove(journal) }
    if size(f)==a.bytes {
      do { let proof=try VerifiedArtifact.verify(pack,index:index,file:f,cancel:cancel);try PackFiles.remove(journal);return proof }
      catch { try cancel.check();try reset();throw error }
    }
    var etag: String?,offset: Int64=0
    if size(journal)>0 && size(journal)<=1024,let bytes=try? Data(contentsOf:journal),let o=(try? JSONSerialization.jsonObject(with:bytes)) as? [String:Any],Set(o.keys)==["digest","index","etag"],o["digest"] as? String==pack.digest,o["index"] as? Int==index,let e=o["etag"] as? String,PackTransport.strongEtag(e),size(f)>0,size(f)<a.bytes { etag=e;offset=size(f) }
    if offset==0 { try reset() }
    let save: (String?)throws->Void = { validator in
      try cancel.check()
      if let e=validator { try PackFiles.atomic(journal,JSONSerialization.data(withJSONObject:["digest":pack.digest,"index":index,"etag":e])) }
      else { try PackFiles.remove(journal) }
    }
    do { try transport.transfer(pack,index:index,file:f,cancel:cancel,offset:offset,etag:etag,validator:save) }
    catch is PackRestartRequired { try cancel.check();try reset();try transport.transfer(pack,index:index,file:f,cancel:cancel,validator:save) }
    do { let proof=try VerifiedArtifact.verify(pack,index:index,file:f,cancel:cancel);try PackFiles.remove(journal);return proof }
    catch { try cancel.check();try reset();throw error }
  }
}
