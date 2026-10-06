import Foundation
import CryptoKit
import XCTest
@testable import NativeTestSeam
final class PackSignatureTests: XCTestCase {
 func testSharedOpenSslVectorVerifiesExactWireFormat() throws {
  func bytes(_ hex: String) -> Data { var data=Data();var i=hex.startIndex;while i<hex.endIndex { let next=hex.index(i,offsetBy:2);data.append(UInt8(hex[i..<next],radix:16)!);i=next };return data }
  let p=try VerifiedPack.verify(payload:PackFixtures.payload,signature:bytes("3045022100cd5d8c97ac16144866d24c916c864634f8ed756695e3236e9463c3a8e705953c0220687f9989ae1a385c631b164e887a53f6c795bcea0322e12531d767dd8e6634dd"),keyID:"vector",algorithm:"ES256",trust:["vector":bytes("3059301306072a8648ce3d020106082a8648ce3d03010703420004d2e47e7184a3b316ff8701e945c498cebf4796c71143854cb09113dbc38e2e957f86f44fb89059a3693aaf38dcfb6681e5d6f5645b3e28cc5700ae4b24d838ca")],runtime:PackFixtures.runtime)
  XCTAssertEqual(p.manifest.packID,"test-pack")
 }
 func testAuthenticatesExactBytesAndRejectsUnknownTrust() throws {
  let key=P256.Signing.PrivateKey(), p=PackFixtures.payload, s=try key.signature(for:p).derRepresentation, trust=["test-key":key.publicKey.derRepresentation]
  XCTAssertEqual(try VerifiedPack.verify(payload:p,signature:s,keyID:"test-key",algorithm:"ES256",trust:trust,runtime:PackFixtures.runtime).manifest.packID,"test-pack")
  var tampered=p;tampered[0]=0
  for (payload,id,algo,sig) in [(tampered,"test-key","ES256",s),(p,"unknown","ES256",s),(p,"test-key","none",s),(p,"test-key","ES256",Data(repeating:0,count:64))] {
   XCTAssertThrowsError(try VerifiedPack.verify(payload:payload,signature:sig,keyID:id,algorithm:algo,trust:trust,runtime:PackFixtures.runtime))
  }
  XCTAssertThrowsError(try VerifiedPack.verify(payload:p,signature:s,keyID:"test-key",algorithm:"ES256",trust:[:],runtime:PackFixtures.runtime))
 }
}
