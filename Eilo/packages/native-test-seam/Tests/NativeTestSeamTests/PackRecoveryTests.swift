import Foundation
import XCTest
@testable import NativeTestSeam
final class InterruptedPackServer: PackHTTPClient {
 var mode=0;var offsets: [Int64]=[]
 func fetch(_ request: PackRequest,cancel: PackCancellation,response: @escaping (PackHeaders)throws->Void,chunk: @escaping (Data)throws->Void) throws {
  offsets.append(request.offset)
  if mode==0 { try response(PackHeaders(status:200,length:4,etag:"\"one\""));try chunk(Data([1,2]));throw PackFailure.transport }
  if request.offset==2 { try response(PackHeaders(status:206,length:2,etag:mode==2 ? "\"two\"":"\"one\"",range:"bytes 2-3/4"));try chunk(Data([3,4])) }
  else { try response(PackHeaders(status:200,length:4,etag:"\"two\""));try chunk(Data([1,2,3,4])) }
 }
}
final class PackRecoveryTests: XCTestCase {
 func testInterruptionResumesAndReverifiesWholeFile() throws {
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString);defer { try? FileManager.default.removeItem(at:root) };let server=InterruptedPackServer(),r=PackRecovery(transport:PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:server)),p=try PackFixtures.verified()
  XCTAssertThrowsError(try r.download(p,index:0,staging:root,cancel:PackCancellation()));server.mode=1
  XCTAssertEqual(try Data(contentsOf:r.download(p,index:0,staging:root,cancel:PackCancellation()).file),Data([1,2,3,4]));XCTAssertEqual(server.offsets,[0,2])
 }
 func testChangedEtagRestartsAndInvalidJournalCannotResume() throws {
  for tamper in [false,true] {
   let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString);defer { try? FileManager.default.removeItem(at:root) };let server=InterruptedPackServer(),r=PackRecovery(transport:PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:server)),p=try PackFixtures.verified()
   XCTAssertThrowsError(try r.download(p,index:0,staging:root,cancel:PackCancellation()));server.mode=2
   if tamper { try Data("{}".utf8).write(to:root.appendingPathComponent("model.gguf.resume")) }
   XCTAssertEqual(try Data(contentsOf:r.download(p,index:0,staging:root,cancel:PackCancellation()).file),Data([1,2,3,4]));XCTAssertEqual(server.offsets,tamper ? [0,0]:[0,2,0])
  }
 }
}
