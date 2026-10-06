import Foundation
import XCTest
@testable import NativeTestSeam
final class FakePackServer: PackHTTPClient {
 var headers=PackHeaders(status:200,length:4,etag:"\"one\"");var body=Data([1,2,3,4]);var requests: [PackRequest]=[]
 func fetch(_ request: PackRequest,cancel: PackCancellation,response: @escaping (PackHeaders)throws->Void,chunk: @escaping (Data)throws->Void) throws { requests.append(request);try response(headers);if (200...299).contains(headers.status) { try chunk(body) } }
}
final class PackTransportTests: XCTestCase {
 func testGenericRequestAndBoundedWrite() throws {
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString);try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true);defer { try? FileManager.default.removeItem(at:root) }
  let f=root.appendingPathComponent("part"),server=FakePackServer(),t=PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:server)
  XCTAssertEqual(try t.transfer(PackFixtures.verified(),index:0,file:f,cancel:PackCancellation()),"\"one\"");XCTAssertEqual(try Data(contentsOf:f),Data([1,2,3,4]));XCTAssertEqual(server.requests.count,1);XCTAssertNil(server.requests[0].etag);XCTAssertEqual(server.requests[0].offset,0)
 }
 func testForeignRedirectAndUnconfiguredOriginNeverRequested() throws {
  let f=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString),server=FakePackServer();server.headers=PackHeaders(status:302,length:0,location:"https://foreign.example.test/file")
  XCTAssertThrowsError(try PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:server).transfer(PackFixtures.verified(),index:0,file:f,cancel:PackCancellation()));XCTAssertEqual(server.requests.count,1);XCTAssertFalse(FileManager.default.fileExists(atPath:f.path))
  let empty=FakePackServer();XCTAssertThrowsError(try PackTransport(policy:PackOriginPolicy(origins:[]),client:empty).transfer(PackFixtures.verified(),index:0,file:f,cancel:PackCancellation()));XCTAssertTrue(empty.requests.isEmpty)
 }
 func testCancellationLengthAndEncodingFailClosed() throws {
  let f=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
  for h in [PackHeaders(status:200,length:5),PackHeaders(status:200,length:4,encoding:"gzip"),PackHeaders(status:401,length:4)] {
   let server=FakePackServer();server.headers=h
   XCTAssertThrowsError(try PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:server).transfer(PackFixtures.verified(),index:0,file:f,cancel:PackCancellation()));XCTAssertFalse(FileManager.default.fileExists(atPath:f.path))
  }
  let cancel=PackCancellation();cancel.cancel();let server=FakePackServer()
  XCTAssertThrowsError(try PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:server).transfer(PackFixtures.verified(),index:0,file:f,cancel:cancel));XCTAssertTrue(server.requests.isEmpty)
 }
}
