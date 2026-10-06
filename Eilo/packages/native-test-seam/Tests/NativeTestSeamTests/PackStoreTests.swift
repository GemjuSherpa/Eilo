import Foundation
import CryptoKit
import XCTest
@testable import NativeTestSeam
final class PackStoreTests: XCTestCase {
 func testFailuresKeepOldVersionAndCommitHasNoMixedFiles() throws {
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString);try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true);defer { try? FileManager.default.removeItem(at:root) }
  let key=P256.Signing.PrivateKey(),trust=["test-key":key.publicKey.derRepresentation]
  func pack(_ revision: Int) throws -> VerifiedPack { let bytes=Data(String(data:PackFixtures.payload,encoding:.utf8)!.replacingOccurrences(of:"\"revision\":1",with:"\"revision\":\(revision)").utf8);return try VerifiedPack.verify(payload:bytes,signature:key.signature(for:bytes).derRepresentation,keyID:"test-key",algorithm:"ES256",trust:trust,runtime:PackFixtures.runtime) }
  let store=PackStore(root:root.appendingPathComponent("store"),trust:trust,runtime:PackFixtures.runtime,licenseEvidence:[String(repeating:"c",count:64)]),file=root.appendingPathComponent("model");try Data([1,2,3,4]).write(to:file)
  let first=try pack(1);try store.activate(first,proofs:[VerifiedArtifact.verify(first,index:0,file:file)],cancel:PackCancellation());XCTAssertEqual(try store.active()?.digest,first.digest)
  for (i,boundary) in [PackActivationStep.copied,.verified,.beforePointer].enumerated() {
   let next=try pack(i+2);XCTAssertThrowsError(try store.activate(next,proofs:[VerifiedArtifact.verify(next,index:0,file:file)],cancel:PackCancellation()) { if $0==boundary { throw PackFailure.activation } });XCTAssertEqual(try store.active()?.digest,first.digest)
  }
  let next=try pack(5);XCTAssertThrowsError(try store.activate(next,proofs:[VerifiedArtifact.verify(next,index:0,file:file)],cancel:PackCancellation()) { if $0 == .afterPointer { throw PackFailure.activation } })
  XCTAssertEqual(try PackStore(root:root.appendingPathComponent("store"),trust:trust,runtime:PackFixtures.runtime,licenseEvidence:[String(repeating:"c",count:64)]).active()?.digest,next.digest)
  XCTAssertThrowsError(try store.activate(first,proofs:[VerifiedArtifact.verify(first,index:0,file:file)],cancel:PackCancellation()))
  try Data([1,2,3,5]).write(to:store.file(next,index:0));XCTAssertThrowsError(try store.active())
 }
 func testStaleProofMissingLicenseAndEmptyTrustCannotActivate() throws {
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString);try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true);defer { try? FileManager.default.removeItem(at:root) }
  let (p,trust)=try PackFixtures.signed(),f=root.appendingPathComponent("part");try Data([1,2,3,4]).write(to:f);let proof=try VerifiedArtifact.verify(p,index:0,file:f)
  for t in [trust,[:]] { XCTAssertThrowsError(try PackStore(root:root.appendingPathComponent("store"),trust:t,runtime:PackFixtures.runtime).activate(p,proofs:[proof],cancel:PackCancellation())) }
  let s=PackStore(root:root.appendingPathComponent("store"),trust:trust,runtime:PackFixtures.runtime,licenseEvidence:[String(repeating:"c",count:64)]);try Data([9,9,9,9]).write(to:f);XCTAssertThrowsError(try s.activate(p,proofs:[proof],cancel:PackCancellation()));XCTAssertNil(try s.active())
 }
}
