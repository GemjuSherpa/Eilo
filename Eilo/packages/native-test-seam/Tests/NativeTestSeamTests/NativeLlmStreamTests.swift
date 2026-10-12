import XCTest
@testable import NativeTestSeam

final class NativeLlmStreamTests: XCTestCase {
  private final class Backend {
    var valid = true, creates = 0, loads = 0, begins = 0, destroys = 0
    var createAvailable = true, loadResult: Int32 = 0, beginResult: Int32 = 0
    var nextResult: Int32 = 1, reportedBytes: Int32 = 1
    var onCreate: () -> Void = {}, onLoad: () -> Void = {}, onBegin: () -> Void = {}
    var onNext: () -> Void = {}
    var pristine = true
    private let mutex = NSLock()
    private var cancellations = 0
    var cancelCount: Int { mutex.lock(); defer { mutex.unlock() }; return cancellations }
    var api: NativeLlmAPI {
      NativeLlmAPI(create: {
        self.creates += 1; self.onCreate()
        return self.createAvailable ? OpaquePointer(bitPattern: 1) : nil
      }, load: { _, fd, threads in
        XCTAssertEqual(fd, 9); XCTAssertEqual(threads, 2)
        self.loads += 1; self.onLoad(); return self.loadResult
      }, begin: { _, bytes, limit in
        XCTAssertEqual(Array(bytes), Array("generic".utf8)); XCTAssertEqual(limit, 8)
        self.begins += 1; self.onBegin(); return self.beginResult
      }, next: { _, buffer, bytes in
        XCTAssertEqual(buffer.count, 1024)
        self.pristine = self.pristine && buffer.allSatisfy { $0 == 0 }
        buffer[0] = CChar(bitPattern: 0xe2); buffer[1] = CChar(bitPattern: 0x82)
        bytes = self.reportedBytes; self.onNext(); return self.nextResult
      }, cancel: { _ in
        self.mutex.lock(); self.cancellations += 1; self.mutex.unlock()
      }, destroy: { _ in self.destroys += 1 })
    }
  }
  private func opened(_ backend: Backend) throws -> NativeLlmStream {
    try NativeLlmStream(allowed: { backend.valid }, api: backend.api)
  }
  private func generating(_ backend: Backend) throws -> NativeLlmStream {
    let stream = try opened(backend)
    try stream.load(verifiedDescriptor: 9)
    try Array("generic".utf8).withUnsafeBufferPointer { try stream.begin($0, outputLimit: 8) }
    return stream
  }
  func testDefaultIsUnavailable() {
    XCTAssertThrowsError(try NativeLlmStream(allowed: { true }))
  }
  func testInvalidLeaseDoesNotCreateAndCreateFailureIsTyped() {
    let b = Backend(); b.valid = false
    XCTAssertThrowsError(try opened(b)); XCTAssertEqual(b.creates, 0)
    b.valid = true; b.createAvailable = false
    XCTAssertThrowsError(try opened(b)); XCTAssertEqual(b.destroys, 0)
  }
  func testLeaseRevokedDuringCreateDestroysCandidate() {
    let b = Backend(); b.onCreate = { b.valid = false }
    XCTAssertThrowsError(try opened(b)); XCTAssertEqual(b.destroys, 1)
  }
  func testCancellationBeforeLoadIsPermanent() throws {
    let b = Backend(), s = try opened(b)
    s.requestCancellation()
    XCTAssertThrowsError(try s.load(verifiedDescriptor: 9)) { error in
      guard case LlmFailure.cancelled = error else { return XCTFail("wrong fixed error") }
    }
    XCTAssertEqual(b.loads, 0); s.close(); XCTAssertEqual(b.destroys, 1)
  }
  func testDescriptorAndThreadBoundsBeforeNativeCall() throws {
    for (fd, threads) in [(Int32(-1), 2), (9, 0), (9, 9)] {
      let b = Backend(), s = try opened(b)
      XCTAssertThrowsError(try s.load(verifiedDescriptor: fd, threads: threads))
      XCTAssertEqual(b.loads, 0); XCTAssertEqual(b.destroys, 1)
    }
  }
  func testLoadFailureAndLeaseRevocationCannotBegin() throws {
    for revoke in [false, true] {
      let b = Backend(), s = try opened(b)
      b.loadResult = revoke ? 0 : -3; b.onLoad = { if revoke { b.valid = false } }
      XCTAssertThrowsError(try s.load(verifiedDescriptor: 9))
      XCTAssertThrowsError(try Array("generic".utf8).withUnsafeBufferPointer { try s.begin($0, outputLimit: 8) })
      XCTAssertEqual(b.begins, 0); XCTAssertEqual(b.destroys, 1)
    }
  }
  func testPromptAndOutputBoundsBeforeNativeCall() throws {
    for (prompt, limit) in [([], 8), ([UInt8](repeating: 65, count: 16385), 8), ([0], 8), ([65], 0), ([65], 257)] {
      let b = Backend(), s = try opened(b); try s.load(verifiedDescriptor: 9)
      XCTAssertThrowsError(try prompt.withUnsafeBufferPointer { try s.begin($0, outputLimit: limit) })
      XCTAssertEqual(b.begins, 0); XCTAssertEqual(b.destroys, 1)
    }
  }
  func testBeginFailureAndLeaseRevocationCannotRelease() throws {
    for revoke in [false, true] {
      let b = Backend(), s = try opened(b); try s.load(verifiedDescriptor: 9)
      b.beginResult = revoke ? 0 : -3; b.onBegin = { if revoke { b.valid = false } }
      XCTAssertThrowsError(try Array("generic".utf8).withUnsafeBufferPointer { try s.begin($0, outputLimit: 8) })
      XCTAssertThrowsError(try s.withNextPiece { _ in XCTFail("stale token") })
      XCTAssertEqual(b.destroys, 1)
    }
  }
  func testRawSplitUtf8IsBorrowedAndScratchClearedBetweenPieces() throws {
    let b = Backend(), s = try generating(b); b.reportedBytes = 2
    for _ in 0..<2 {
      XCTAssertTrue(try s.withNextPiece { XCTAssertEqual(Array($0), [0xe2, 0x82]) })
    }
    XCTAssertTrue(b.pristine); s.close(); s.close(); XCTAssertEqual(b.destroys, 1)
  }
  func testCompletionClosesAndCannotReplayOrRestart() throws {
    let b = Backend(), s = try generating(b); b.nextResult = 0; b.reportedBytes = 0
    XCTAssertFalse(try s.withNextPiece { _ in XCTFail("completion emitted bytes") })
    XCTAssertThrowsError(try s.withNextPiece { _ in XCTFail("replayed") })
    XCTAssertThrowsError(try s.load(verifiedDescriptor: 9)); XCTAssertEqual(b.destroys, 1)
  }
  func testMalformedNativeResultCannotRelease() throws {
    for (result, bytes) in [(Int32(1), Int32(0)), (1, -1), (1, 1025), (0, 1), (7, 1), (-3, 0), (-2, 0)] {
      let b = Backend(), s = try generating(b); b.nextResult = result; b.reportedBytes = bytes
      XCTAssertThrowsError(try s.withNextPiece { _ in XCTFail("invalid piece") })
      s.close(); XCTAssertEqual(b.destroys, 1)
    }
  }
  func testRevocationDuringNextSuppressesPiece() throws {
    let b = Backend(), s = try generating(b); b.onNext = { b.valid = false }
    XCTAssertThrowsError(try s.withNextPiece { _ in XCTFail("revoked piece") })
    XCTAssertEqual(b.destroys, 1)
  }
  func testCancellationDuringEachNativeOperationSuppressesRelease() throws {
    for step in 0..<3 {
      let b = Backend(), s = try opened(b)
      if step == 0 { b.onLoad = { s.requestCancellation() } }
      if step == 1 { b.onBegin = { s.requestCancellation() } }
      if step == 2 { b.onNext = { s.requestCancellation() } }
      XCTAssertThrowsError(try {
        try s.load(verifiedDescriptor: 9)
        try Array("generic".utf8).withUnsafeBufferPointer { try s.begin($0, outputLimit: 8) }
        _ = try s.withNextPiece { _ in XCTFail("cancelled piece") }
      }())
      XCTAssertEqual(b.destroys, 1)
    }
  }
  func testCancelDoesNotWaitForOrDestroyBlockedDecode() throws {
    let b = Backend(), s = try generating(b)
    let entered = DispatchSemaphore(value: 0), release = DispatchSemaphore(value: 0)
    let finished = expectation(description: "worker joined")
    b.onNext = { entered.signal(); _ = release.wait(timeout: .now() + 5) }
    DispatchQueue.global().async {
      do {
        _ = try s.withNextPiece { _ in XCTFail("cancelled piece") }
        XCTFail("cancelled call succeeded")
      } catch { }
      s.close(); finished.fulfill()
    }
    XCTAssertEqual(entered.wait(timeout: .now() + 5), .success)
    s.requestCancellation(); XCTAssertEqual(b.cancelCount, 1)
    release.signal(); wait(for: [finished], timeout: 5)
    XCTAssertEqual(b.destroys, 1)
    s.requestCancellation(); XCTAssertEqual(b.cancelCount, 2)
  }
  func testDeinitClosesAnUnusedHandleOnce() throws {
    let b = Backend()
    var s: NativeLlmStream? = try opened(b)
    XCTAssertNotNil(s); s = nil
    XCTAssertEqual(b.destroys, 1)
  }
}
