import Foundation
public final class PackCancellation: @unchecked Sendable {
  private let lock=NSLock();private var cancelled=false
  public init() {}
  public func cancel() { lock.lock();cancelled=true;lock.unlock() }
  public func check() throws { lock.lock();defer { lock.unlock() };if cancelled { throw PackFailure.cancelled } }
}
public struct PackRequest: Sendable { public let url: String;public let offset: Int64;public let etag: String? }
public struct PackHeaders { public let status: Int;public let length: Int64;public var location,etag,range,encoding: String? }
public protocol PackHTTPClient { func fetch(_ request: PackRequest,cancel: PackCancellation,response: @escaping (PackHeaders)throws->Void,chunk: @escaping (Data)throws->Void) throws }
/// Ephemeral session, no cookies, credentials, cache, or automatic redirects; streaming writes are bounded by transport.
public final class NativePackHTTPClient: PackHTTPClient {
  public init() {}
  public func fetch(_ request: PackRequest,cancel: PackCancellation,response: @escaping (PackHeaders)throws->Void,chunk: @escaping (Data)throws->Void) throws {
    guard !Thread.isMainThread, let url=URL(string:request.url) else { throw PackFailure.transport };try cancel.check()
    let config=URLSessionConfiguration.ephemeral;config.urlCache=nil;config.httpCookieStorage=nil;config.urlCredentialStorage=nil;config.httpShouldSetCookies=false
    config.requestCachePolicy = .reloadIgnoringLocalCacheData;config.timeoutIntervalForRequest=15;config.timeoutIntervalForResource=120
    config.tlsMinimumSupportedProtocolVersion = .TLSv12
    let delegate=PackStreamDelegate(cancel:cancel,response:response,chunk:chunk)
    let queue=OperationQueue();queue.maxConcurrentOperationCount=1
    let session=URLSession(configuration:config,delegate:delegate,delegateQueue:queue)
    defer { session.invalidateAndCancel() }
    var r=URLRequest(url:url);r.httpMethod="GET";r.setValue("identity",forHTTPHeaderField:"Accept-Encoding");r.setValue("Eilo-Model-Installer/1",forHTTPHeaderField:"User-Agent")
    if request.offset>0 { r.setValue("bytes=\(request.offset)-",forHTTPHeaderField:"Range");r.setValue(request.etag,forHTTPHeaderField:"If-Range") }
    let task=session.dataTask(with:r);task.resume()
    var wasCancelled=false
    while delegate.done.wait(timeout:.now()+0.1) == .timedOut { do { try cancel.check() } catch { wasCancelled=true;task.cancel() } }
    if wasCancelled { throw PackFailure.cancelled }
    if let failure=delegate.failure { throw failure }
  }
}
private final class PackStreamDelegate: NSObject, URLSessionDataDelegate, @unchecked Sendable {
  let cancel: PackCancellation;let response: (PackHeaders)throws->Void;let chunk: (Data)throws->Void
  let done=DispatchSemaphore(value:0);var failure: Error?
  init(cancel: PackCancellation,response: @escaping (PackHeaders)throws->Void,chunk: @escaping (Data)throws->Void) { self.cancel=cancel;self.response=response;self.chunk=chunk }
  func urlSession(_ session: URLSession,task: URLSessionTask,willPerformHTTPRedirection response: HTTPURLResponse,newRequest request: URLRequest,completionHandler: @escaping (URLRequest?)->Void) { completionHandler(nil) }
  func urlSession(_ session: URLSession,task: URLSessionTask,didReceive challenge: URLAuthenticationChallenge,completionHandler: @escaping (URLSession.AuthChallengeDisposition,URLCredential?)->Void) {
    completionHandler(challenge.protectionSpace.authenticationMethod==NSURLAuthenticationMethodServerTrust ? .performDefaultHandling : .cancelAuthenticationChallenge,nil)
  }
  func urlSession(_ session: URLSession,dataTask: URLSessionDataTask,didReceive reply: URLResponse,completionHandler: @escaping (URLSession.ResponseDisposition)->Void) {
    do {
      try cancel.check();guard let h=reply as? HTTPURLResponse else { throw PackFailure.transport }
      try response(PackHeaders(status:h.statusCode,length:h.expectedContentLength,location:h.value(forHTTPHeaderField:"Location"),etag:h.value(forHTTPHeaderField:"ETag"),range:h.value(forHTTPHeaderField:"Content-Range"),encoding:h.value(forHTTPHeaderField:"Content-Encoding")))
      completionHandler((200...299).contains(h.statusCode) ? .allow : .cancel)
    } catch { failure=error;completionHandler(.cancel) }
  }
  func urlSession(_ session: URLSession,dataTask: URLSessionDataTask,didReceive data: Data) { do { try cancel.check();try chunk(data) } catch { failure=error;dataTask.cancel() } }
  func urlSession(_ session: URLSession,task: URLSessionTask,didCompleteWithError error: Error?) {
    // Redirect response deliberately cancels its body; transport decides the next allowlisted request.
    if failure==nil, let error=error as NSError?, error.code != NSURLErrorCancelled { failure=PackFailure.transport }
    done.signal()
  }
}
public struct PackOriginPolicy {
  private let origins: Set<String>
  public init(origins: Set<String>) { self.origins=origins }
  public func allows(_ url: String) -> Bool {
    guard let u=URLComponents(string:url),let host=u.host,let parsed=URL(string:url) else { return false }
    return u.scheme=="https" && u.user==nil && u.password==nil && u.query==nil && u.fragment==nil && (u.port==nil || u.port==443) && !u.percentEncodedPath.contains("%") && !u.path.contains("\\") && parsed.standardized.absoluteString==url && host.range(of:"^[a-z0-9.-]+$",options:.regularExpression) != nil && host != "localhost" && host.range(of:"^[0-9.]+$",options:.regularExpression)==nil && origins.contains("https://"+host)
  }
}
public struct PackRestartRequired: Error {}
public final class PackTransport {
  private let policy: PackOriginPolicy;private let client: any PackHTTPClient
  public init(policy: PackOriginPolicy,client: any PackHTTPClient=NativePackHTTPClient()) { self.policy=policy;self.client=client }
  public static func strongEtag(_ s: String?) -> Bool { s?.range(of:#"^"[a-zA-Z0-9._-]{1,128}"$"#,options:.regularExpression) != nil }
  @discardableResult public func transfer(_ pack: VerifiedPack,index: Int,file: URL,cancel: PackCancellation,offset: Int64=0,etag: String?=nil) throws -> String? {
    guard pack.manifest.artifacts.indices.contains(index) else { throw PackFailure.manifest };let a=pack.manifest.artifacts[index]
    guard offset>=0 && offset<a.bytes && (offset==0 || Self.strongEtag(etag)) else { throw PackFailure.transport }
    if offset>0 { guard try FileManager.default.attributesOfItem(atPath:file.path)[.size] as? Int64 == offset else { throw PackFailure.transport } }
    var url=a.url,redirects=0
    while true {
      try cancel.check();guard policy.allows(url) else { throw PackFailure.origin }
      var redirect: String?,nextEtag: String?,received: Int64=0,accepted=false,output: FileHandle?
      defer { try? output?.close() }
      try client.fetch(PackRequest(url:url,offset:offset,etag:offset>0 ? etag : nil),cancel:cancel,response: { h in
        if [301,302,303,307,308].contains(h.status) { guard redirects<4,let location=h.location,let base=URL(string:url),let next=URL(string:location,relativeTo:base)?.absoluteURL else { throw PackFailure.transport };redirect=next.absoluteString }
        else {
          if offset>0 && (h.status != 206 || h.etag != etag) { throw PackRestartRequired() }
          guard h.status==(offset>0 ? 206:200),h.length==a.bytes-offset,h.encoding==nil || h.encoding=="identity" else { throw PackFailure.transport }
          if offset>0 && h.range != "bytes \(offset)-\(a.bytes-1)/\(a.bytes)" { throw PackFailure.transport }
          try cancel.check();nextEtag=Self.strongEtag(h.etag) ? h.etag:nil
          if offset==0 { guard FileManager.default.createFile(atPath:file.path,contents:nil) else { throw PackFailure.transport } }
          output=try FileHandle(forWritingTo:file);if offset>0 { try output?.seekToEnd() };accepted=true
        }
      },chunk: { data in
        try cancel.check();guard accepted && Int64(data.count)<=a.bytes-offset-received else { throw PackFailure.transport }
        try output?.write(contentsOf:data);received+=Int64(data.count)
      })
      if let next=redirect { url=next;redirects+=1;continue }
      guard accepted && received==a.bytes-offset else { throw PackFailure.transport };try output?.synchronize();try output?.close();output=nil;return nextEtag
    }
  }
}
