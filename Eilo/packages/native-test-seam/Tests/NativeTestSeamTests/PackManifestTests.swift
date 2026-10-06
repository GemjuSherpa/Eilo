import Foundation
import CryptoKit
import XCTest
@testable import NativeTestSeam
enum PackFixtures { static let runtime="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"; static func verified(_ bytes: Data=payload) throws -> VerifiedPack { let key=P256.Signing.PrivateKey();return try VerifiedPack.verify(payload:bytes,signature:key.signature(for:bytes).derRepresentation,keyID:"test-key",algorithm:"ES256",trust:["test-key":key.publicKey.derRepresentation],runtime:runtime) }; static let payload=Data(#"{"schema":1,"packId":"test-pack","revision":1,"runtimeRevision":"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa","minAndroid":35,"minIos":18,"artifacts":[{"id":"llm","filename":"model.gguf","role":"llm","url":"https://models.example.test/model.gguf","sha256":"bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb","bytes":4,"license":"Apache-2.0","licenseEvidence":"cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"}]}"#.utf8) }
final class PackManifestTests: XCTestCase {
 func testValidMetadata() throws { XCTAssertEqual(try PackManifest.parse(PackFixtures.payload,runtime:PackFixtures.runtime).artifacts.first?.bytes,4) }
 func testRejectsUnsafeAndIncomplete() {
  let s=String(data:PackFixtures.payload,encoding:.utf8)!
  let changes=[("model.gguf","../model.gguf"),("https://","http://"),("Apache-2.0","unknown"),("\"schema\":1","\"schema\":2"),("\"bytes\":4","\"bytes\":4.0"),("\"revision\":1","\"revision\":1,\"revision\":2"),("\"packId\"","\"unexpected\""),("model.gguf\"","model.gguf?tracking=1\"" )]
  for (a,b) in changes { XCTAssertThrowsError(try PackManifest.parse(Data(s.replacingOccurrences(of:a,with:b).utf8),runtime:PackFixtures.runtime)) }
 }
 func testRejectsRuntimePlatformAndBounds() {
  XCTAssertThrowsError(try PackManifest.parse(PackFixtures.payload,runtime:String(repeating:"d",count:40)))
  XCTAssertThrowsError(try PackManifest.parse(PackFixtures.payload,runtime:PackFixtures.runtime,ios:17))
  XCTAssertThrowsError(try PackManifest.parse(Data(repeating:32,count:65537),runtime:PackFixtures.runtime))
 }
}
