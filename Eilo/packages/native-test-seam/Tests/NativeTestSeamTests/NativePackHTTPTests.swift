import Foundation
import XCTest
@testable import NativeTestSeam

private struct OfflineReply {
 let status:Int
 var headers:[String:String]=[:]
 var chunks:[Data]=[]
 var hold=false
 var error:URLError?
}
private final class OfflineHTTPState:@unchecked Sendable {
 let lock=NSLock()
 var replies:[String:OfflineReply]=[:]
 var requests:[URLRequest]=[]
 var onRequest:(()->Void)?
 func reset(_ reply:OfflineReply) { lock.lock();defer { lock.unlock() };replies=["https://models.example.test/model.gguf":reply];requests=[];onRequest=nil }
 func afterRequest(_ action:@escaping ()->Void) { lock.lock();defer { lock.unlock() };onRequest=action }
 func receive(_ request:URLRequest)->OfflineReply? { lock.lock();requests.append(request);let reply=replies[request.url?.absoluteString ?? ""],action=onRequest;lock.unlock();action?();return reply }
 func snapshot()->[URLRequest] { lock.lock();defer { lock.unlock() };return requests }
}
/// Intercepts every request in its private session; unknown URLs fail locally, never fall through.
private final class OfflinePackURLProtocol:URLProtocol,@unchecked Sendable {
 static let state=OfflineHTTPState()
 override class func canInit(with request:URLRequest)->Bool { true }
 override class func canonicalRequest(for request:URLRequest)->URLRequest { request }
 override func startLoading() {
  guard let reply=Self.state.receive(request),let url=request.url else { client?.urlProtocol(self,didFailWithError:URLError(.unsupportedURL));return }
  if reply.hold { return }
  if let error=reply.error { client?.urlProtocol(self,didFailWithError:error);return }
  guard let response=HTTPURLResponse(url:url,statusCode:reply.status,httpVersion:"HTTP/1.1",headerFields:reply.headers) else { client?.urlProtocol(self,didFailWithError:URLError(.badServerResponse));return }
  client?.urlProtocol(self,didReceive:response,cacheStoragePolicy:.notAllowed)
  for chunk in reply.chunks { client?.urlProtocol(self,didLoad:chunk) }
  client?.urlProtocolDidFinishLoading(self)
 }
 override func stopLoading() {}
}

final class NativePackHTTPTests:XCTestCase {
 private func client()->NativePackHTTPClient { NativePackHTTPClient(protocolClasses:[OfflinePackURLProtocol.self]) }
 private func background(_ work:@escaping ()throws->Void,file:StaticString=#filePath,line:UInt=#line) {
  let done=expectation(description:"offline native HTTP completion")
  DispatchQueue.global().async { defer { done.fulfill() };do { try work() } catch { XCTFail("unexpected offline adapter error: \(type(of:error))",file:file,line:line) } }
  wait(for:[done],timeout:10)
 }
 private func root() throws -> URL {
  let path=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
  try FileManager.default.createDirectory(at:path,withIntermediateDirectories:true);addTeardownBlock { try? FileManager.default.removeItem(at:path) };return path
 }
 func testEphemeralSessionHasNoSharedPersistence() {
  let config=NativePackHTTPClient.configuration()
  XCTAssertNil(config.urlCache);XCTAssertNil(config.httpCookieStorage);XCTAssertNil(config.urlCredentialStorage)
  XCTAssertFalse(config.httpShouldSetCookies);XCTAssertEqual(config.requestCachePolicy,.reloadIgnoringLocalCacheData)
  XCTAssertEqual(config.timeoutIntervalForRequest,15);XCTAssertEqual(config.timeoutIntervalForResource,120)
  XCTAssertEqual(config.tlsMinimumSupportedProtocolVersion,.TLSv12)
 }
 func testNativeClientRejectsInsecureAndCredentialURLsBeforeSession() {
  let client=client();OfflinePackURLProtocol.state.reset(OfflineReply(status:200,headers:["Content-Length":"4"],chunks:[Data([1,2,3,4])]))
  background {
   for url in ["http://models.example.test/model.gguf","file:///synthetic-eilo-fixture","not-a-url","https://user:password@models.example.test/model.gguf"] {
    XCTAssertThrowsError(try client.fetch(PackRequest(url:url,offset:0,etag:nil),cancel:PackCancellation(),response:{ _ in XCTFail("denied response delivered") },chunk:{ _ in XCTFail("denied body delivered") }))
   }
  }
  XCTAssertTrue(OfflinePackURLProtocol.state.snapshot().isEmpty)
 }
 func testActualRequestHeadersAndStreamingBytes() throws {
  let file=try root().appendingPathComponent("part"),client=client(),pack=try PackFixtures.verified()
  OfflinePackURLProtocol.state.reset(OfflineReply(status:200,headers:["Content-Length":"4","ETag":"\"one\"","Set-Cookie":"synthetic=fixture"],chunks:[Data([1,2]),Data([3,4])]))
  background {
   let transport=PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:client)
   XCTAssertEqual(try transport.transfer(pack,index:0,file:file,cancel:PackCancellation()),"\"one\"")
   XCTAssertEqual(try Data(contentsOf:file),Data([1,2,3,4]))
  }
  let requests=OfflinePackURLProtocol.state.snapshot();XCTAssertEqual(requests.count,1)
  let request=try XCTUnwrap(requests.first)
  XCTAssertEqual(request.httpMethod,"GET");XCTAssertNil(request.httpBody)
  XCTAssertEqual(request.value(forHTTPHeaderField:"Accept-Encoding"),"identity")
  XCTAssertEqual(request.value(forHTTPHeaderField:"User-Agent"),"Eilo-Model-Installer/1")
  for header in ["Cookie","Authorization","Proxy-Authorization","Range","If-Range"] { XCTAssertNil(request.value(forHTTPHeaderField:header)) }
  XCTAssertFalse(request.httpShouldHandleCookies);XCTAssertEqual(request.cachePolicy,.reloadIgnoringLocalCacheData);XCTAssertEqual(request.timeoutInterval,15)
 }
 func testResumeUsesExactRangeAndValidator() throws {
  let file=try root().appendingPathComponent("part"),client=client(),pack=try PackFixtures.verified();try Data([1,2]).write(to:file)
  OfflinePackURLProtocol.state.reset(OfflineReply(status:206,headers:["Content-Length":"2","Content-Range":"bytes 2-3/4","ETag":"\"one\""],chunks:[Data([3,4])]))
  background {
   _=try PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:client).transfer(pack,index:0,file:file,cancel:PackCancellation(),offset:2,etag:"\"one\"")
   XCTAssertEqual(try Data(contentsOf:file),Data([1,2,3,4]))
  }
  let r=try XCTUnwrap(OfflinePackURLProtocol.state.snapshot().first)
  XCTAssertEqual(r.value(forHTTPHeaderField:"Range"),"bytes=2-");XCTAssertEqual(r.value(forHTTPHeaderField:"If-Range"),"\"one\"")
 }
 func testResponseCookieIsNotReplayedOnNextFetch() {
  let client=client(),request=PackRequest(url:"https://models.example.test/model.gguf",offset:0,etag:nil)
  OfflinePackURLProtocol.state.reset(OfflineReply(status:200,headers:["Content-Length":"4","Set-Cookie":"synthetic=fixture; Secure; Path=/"],chunks:[Data([1,2,3,4])]))
  background {
   for _ in 0..<2 {
    var received=Data()
    try client.fetch(request,cancel:PackCancellation(),response:{ h in XCTAssertEqual(h.status,200) },chunk:{ received.append($0) })
    XCTAssertEqual(received,Data([1,2,3,4]))
   }
  }
  let requests=OfflinePackURLProtocol.state.snapshot();XCTAssertEqual(requests.count,2)
  for r in requests { XCTAssertNil(r.value(forHTTPHeaderField:"Cookie"));XCTAssertNil(r.value(forHTTPHeaderField:"Authorization")) }
 }
 func testRejectedResponsesNeverCreateArtifact() throws {
  let file=try root().appendingPathComponent("part"),client=client(),pack=try PackFixtures.verified()
  for reply in [OfflineReply(status:401,headers:["Content-Length":"4"],chunks:[Data([1,2,3,4])]),
                OfflineReply(status:200,headers:["Content-Length":"5"],chunks:[Data([1,2,3,4])]),
                OfflineReply(status:200,headers:["Content-Length":"4","Content-Encoding":"gzip"],chunks:[Data([1,2,3,4])])] {
   OfflinePackURLProtocol.state.reset(reply)
   background {
    XCTAssertThrowsError(try PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:client).transfer(pack,index:0,file:file,cancel:PackCancellation()))
    XCTAssertFalse(FileManager.default.fileExists(atPath:file.path))
   }
  }
 }
 func testForeignRedirectIsDeniedBeforeSecondRequest() throws {
  let file=try root().appendingPathComponent("part"),client=client(),pack=try PackFixtures.verified()
  OfflinePackURLProtocol.state.reset(OfflineReply(status:302,headers:["Content-Length":"0","Location":"https://foreign.example.test/file"]))
  background {
   XCTAssertThrowsError(try PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:client).transfer(pack,index:0,file:file,cancel:PackCancellation()))
   XCTAssertFalse(FileManager.default.fileExists(atPath:file.path))
  }
  XCTAssertEqual(OfflinePackURLProtocol.state.snapshot().count,1)
 }
 func testCancellationOfPendingNativeTaskCompletes() {
  let client=client(),cancel=PackCancellation()
  OfflinePackURLProtocol.state.reset(OfflineReply(status:200,hold:true))
  OfflinePackURLProtocol.state.afterRequest { cancel.cancel() }
  background {
   XCTAssertThrowsError(try client.fetch(PackRequest(url:"https://models.example.test/model.gguf",offset:0,etag:nil),cancel:cancel,response:{ _ in XCTFail("held response delivered") },chunk:{ _ in XCTFail("held body delivered") })) { error in
    guard case PackFailure.cancelled=error else { XCTFail("wrong cancellation error");return }
   }
  }
  XCTAssertEqual(OfflinePackURLProtocol.state.snapshot().count,1)
 }
 func testNetworkFailureAndPreCancelledRequestHaveNoBytes() {
  let client=client(),request=PackRequest(url:"https://models.example.test/model.gguf",offset:0,etag:nil)
  OfflinePackURLProtocol.state.reset(OfflineReply(status:200,error:URLError(.notConnectedToInternet)))
  background {
   XCTAssertThrowsError(try client.fetch(request,cancel:PackCancellation(),response:{ _ in XCTFail("failed response delivered") },chunk:{ _ in XCTFail("failed body delivered") }))
   let cancelled=PackCancellation();cancelled.cancel()
   XCTAssertThrowsError(try client.fetch(request,cancel:cancelled,response:{ _ in XCTFail("cancelled response delivered") },chunk:{ _ in XCTFail("cancelled body delivered") }))
  }
  XCTAssertEqual(OfflinePackURLProtocol.state.snapshot().count,1)
 }
 func testTruncatedAndOversizedNativeBodiesNeverSucceed() throws {
  let file=try root().appendingPathComponent("part"),client=client(),pack=try PackFixtures.verified()
  for chunks in [[Data([1,2])],[Data([1,2]),Data([3,4,5])]] {
   OfflinePackURLProtocol.state.reset(OfflineReply(status:200,headers:["Content-Length":"4"],chunks:chunks))
   background {
    XCTAssertThrowsError(try PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:client).transfer(pack,index:0,file:file,cancel:PackCancellation()))
    // URLSession may coalesce fixture chunks. Only a bounded, correct prefix may remain.
    let partial=try Data(contentsOf:file)
    XCTAssertLessThan(partial.count,4);XCTAssertEqual(partial,Data([1,2,3,4]).prefix(partial.count))
   }
  }
 }
 func testInvalidResumeRangeLeavesExistingPartialUnchanged() throws {
  let file=try root().appendingPathComponent("part"),client=client(),pack=try PackFixtures.verified();try Data([1,2]).write(to:file)
  OfflinePackURLProtocol.state.reset(OfflineReply(status:206,headers:["Content-Length":"2","Content-Range":"bytes 1-2/4","ETag":"\"one\""],chunks:[Data([3,4])]))
  background {
   XCTAssertThrowsError(try PackTransport(policy:PackOriginPolicy(origins:["https://models.example.test"]),client:client).transfer(pack,index:0,file:file,cancel:PackCancellation(),offset:2,etag:"\"one\""))
   XCTAssertEqual(try Data(contentsOf:file),Data([1,2]))
  }
 }
}
