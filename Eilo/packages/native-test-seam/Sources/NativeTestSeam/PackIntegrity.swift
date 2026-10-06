import Foundation
import CryptoKit
import Darwin
public struct VerifiedArtifact {
  public let file: URL
  public let packDigest: String
  public let index: Int
  private init(file: URL,packDigest: String,index: Int) { self.file=file;self.packDigest=packDigest;self.index=index }
  public static func verify(_ pack: VerifiedPack,index: Int,file: URL,cancel: PackCancellation=PackCancellation()) throws -> VerifiedArtifact {
    guard pack.manifest.artifacts.indices.contains(index) else { throw PackFailure.integrity };let a=pack.manifest.artifacts[index];try cancel.check()
    let fd=open(file.path,O_RDONLY|O_NOFOLLOW);guard fd>=0 else { throw PackFailure.integrity }
    let input=FileHandle(fileDescriptor:fd,closeOnDealloc:true);defer { try? input.close() }
    var before=stat();guard fstat(fd,&before)==0,before.st_mode & S_IFMT == S_IFREG,before.st_size==a.bytes else { throw PackFailure.integrity }
    var digest=SHA256(),count: Int64=0
    while true { try cancel.check();let data=try input.read(upToCount:65536) ?? Data();if data.isEmpty { break };guard Int64(data.count)<=a.bytes-count else { throw PackFailure.integrity };digest.update(data:data);count+=Int64(data.count) }
    var after=stat();guard fstat(fd,&after)==0,count==a.bytes,after.st_size==before.st_size,after.st_ino==before.st_ino,after.st_mtimespec.tv_sec==before.st_mtimespec.tv_sec,after.st_mtimespec.tv_nsec==before.st_mtimespec.tv_nsec else { throw PackFailure.integrity }
    guard digest.finalize().map({ String(format:"%02x",$0) }).joined()==a.sha256 else { throw PackFailure.integrity }
    return VerifiedArtifact(file:file,packDigest:pack.digest,index:index)
  }
}
