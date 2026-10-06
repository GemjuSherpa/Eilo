import Foundation
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
 func testCancellationCannotIssueProof() throws {
  let c=PackCancellation();c.cancel();XCTAssertThrowsError(try VerifiedArtifact.verify(PackFixtures.verified(),index:0,file:URL(fileURLWithPath:"/missing"),cancel:c))
 }
}
