import Foundation
import CryptoKit
import XCTest
@testable import NativeTestSeam
final class PackIntegrityTests: XCTestCase {
 func testExactPassesCorruptPartialAndSymlinkFail() throws {
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString);try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true);defer { try? FileManager.default.removeItem(at:root) }
  let f=root.appendingPathComponent("part"),pack=try PackFixtures.verified();try Data([1,2,3,4]).write(to:f)
  XCTAssertEqual(try VerifiedArtifact.verify(pack,index:0,file:f).packDigest,pack.digest)
  for bytes: [UInt8] in [[1,2],[1,2,3,5],[1,2,3,4,5]] { try Data(bytes).write(to:f);XCTAssertThrowsError(try VerifiedArtifact.verify(pack,index:0,file:f)) }
  try Data([1,2,3,4]).write(to:f);let link=root.appendingPathComponent("link");try FileManager.default.createSymbolicLink(at:link,withDestinationURL:f);XCTAssertThrowsError(try VerifiedArtifact.verify(pack,index:0,file:link))
 }
 func testMultiChunkProofChecksFinalPartialChunkAndRepeatedVerification() throws {
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
  try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
  defer { try? FileManager.default.removeItem(at:root) }
  let file=root.appendingPathComponent("large-part"),bytes=Data(repeating:37,count:2*1024*1024+17)
  try bytes.write(to:file)
  let hash=SHA256.hash(data:bytes).map{String(format:"%02x",$0)}.joined()
  let template=String(data:PackFixtures.payload,encoding:.utf8)!
  let payload=template.replacingOccurrences(of:"9f64a747e1b97f131fabb6b447296c9b6f0201e79fb3c5356e6c77e89b6a806a",with:hash).replacingOccurrences(of:"\"bytes\":4",with:"\"bytes\":\(bytes.count)")
  let pack=try PackFixtures.verified(Data(payload.utf8))
  try autoreleasepool {
   for _ in 0..<3 { XCTAssertEqual(try VerifiedArtifact.verify(pack,index:0,file:file).packDigest,pack.digest) }
  }
  let handle=try FileHandle(forWritingTo:file);try handle.seek(toOffset:UInt64(bytes.count-1));try handle.write(contentsOf:Data([38]));try handle.close()
  XCTAssertThrowsError(try VerifiedArtifact.verify(pack,index:0,file:file))
 }
 func testCancellationCannotIssueProof() throws {
  let c=PackCancellation();c.cancel();XCTAssertThrowsError(try VerifiedArtifact.verify(PackFixtures.verified(),index:0,file:URL(fileURLWithPath:"/missing"),cancel:c))
 }
}
