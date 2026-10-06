import Foundation
import CryptoKit
import XCTest
@testable import NativeTestSeam
final class PackSignatureTests: XCTestCase {
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
