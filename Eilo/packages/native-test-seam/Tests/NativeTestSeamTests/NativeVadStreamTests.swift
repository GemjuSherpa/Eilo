import XCTest
@testable import NativeTestSeam

final class NativeVadStreamTests: XCTestCase {
  private let h = OpaquePointer(bitPattern: 1)!
  private func frame(_ start: Int = 0, _ count: Int = 512, _ final: Bool = false) -> NativeVadObservation {
    NativeVadObservation(probability: 0.9, startSample: start, samples: count, final: final)
  }
  func testDefaultUnavailableAndInvalidPathsDoNotOpen() {
    XCTAssertThrowsError(try NativeVadStream(model: "/synthetic", verified: { true }))
    var opens = 0
    let api = NativeVadAPI(create: { _ in opens += 1; return self.h }, process: { _, _, _ in nil }, destroy: { _ in })
    for path in ["relative", "/bad\0path", "/" + String(repeating: "x", count: 4096)] {
      XCTAssertThrowsError(try NativeVadStream(model: path, verified: { true }, api: api))
    }
    XCTAssertThrowsError(try NativeVadStream(model: "/synthetic", verified: { false }, api: api))
    XCTAssertEqual(opens, 0)
  }
  func testRevocationDuringCreationClosesCandidate() {
    var valid = true, closes = 0
    let api = NativeVadAPI(create: { _ in valid = false; return self.h }, process: { _, _, _ in nil }, destroy: { _ in closes += 1 })
    XCTAssertThrowsError(try NativeVadStream(model: "/synthetic", verified: { valid }, api: api))
    XCTAssertEqual(closes, 1)
  }
  func testRevocationDuringInferenceCannotReleaseFrame() throws {
    var valid = true, closes = 0, calls = 0
    let api = NativeVadAPI(create: { _ in self.h }, process: { _, _, _ in calls += 1; valid = false; return self.frame() }, destroy: { _ in closes += 1 })
    let stream = try NativeVadStream(model: "/synthetic", verified: { valid }, api: api)
    let pcm = [Float](repeating: 0.1, count: 512)
    XCTAssertThrowsError(try pcm.withUnsafeBufferPointer { try stream.process($0, final: false) })
    valid = true
    XCTAssertThrowsError(try pcm.withUnsafeBufferPointer { try stream.process($0, final: false) })
    stream.close(); XCTAssertEqual(closes, 1); XCTAssertEqual(calls, 1)
  }
  func testInvalidInputNeverReachesBackend() throws {
    for (count, final, value): (Int, Bool, Float) in [(0,false,0),(513,true,0),(7,false,0),(512,false,.nan),(512,false,1.1)] {
      var calls = 0, closes = 0
      let api = NativeVadAPI(create: { _ in self.h }, process: { _, _, _ in calls += 1; return self.frame() }, destroy: { _ in closes += 1 })
      let stream = try NativeVadStream(model: "/synthetic", verified: { true }, api: api)
      XCTAssertThrowsError(try [Float](repeating: value, count: count).withUnsafeBufferPointer { try stream.process($0, final: final) })
      XCTAssertEqual(calls, 0); XCTAssertEqual(closes, 1)
    }
  }
  func testInvalidNativeMetadataAndFailureClose() throws {
    let invalid: [NativeVadObservation?] = [nil, frame(1), frame(0,511), frame(0,512,true),
      NativeVadObservation(probability: .nan, startSample: 0, samples: 512, final: false)]
    for value in invalid {
      var closes = 0
      let api = NativeVadAPI(create: { _ in self.h }, process: { _, _, _ in value }, destroy: { _ in closes += 1 })
      let stream = try NativeVadStream(model: "/synthetic", verified: { true }, api: api)
      XCTAssertThrowsError(try [Float](repeating: 0, count: 512).withUnsafeBufferPointer { try stream.process($0, final: false) })
      stream.close(); XCTAssertEqual(closes, 1)
    }
  }
  func testContiguousFinalClosesExactlyOnceAndPreservesCallerPcm() throws {
    var next = 0, closes = 0
    let api = NativeVadAPI(create: { _ in self.h }, process: { _, pcm, final in
      defer { next += pcm.count }; return self.frame(next, pcm.count, final)
    }, destroy: { _ in closes += 1 })
    let stream = try NativeVadStream(model: "/synthetic", verified: { true }, api: api)
    let pcm = [Float](repeating: 0.25, count: 512)
    XCTAssertEqual(try pcm.withUnsafeBufferPointer { try stream.process($0, final: false) }.startSample, 0)
    XCTAssertEqual(try [Float](repeating: 0.25,count:7).withUnsafeBufferPointer { try stream.process($0, final:true) }.samples, 7)
    XCTAssertEqual(pcm, [Float](repeating: 0.25,count:512)); XCTAssertEqual(closes, 1)
    XCTAssertThrowsError(try pcm.withUnsafeBufferPointer { try stream.process($0, final:false) })
    stream.close(); XCTAssertEqual(closes, 1)
  }
  func testRevocationDuringFinalCleanupWithholdsFrame() throws {
    var valid = true
    let api = NativeVadAPI(create: { _ in self.h }, process: { _, pcm, final in self.frame(0,pcm.count,final) }, destroy: { _ in valid = false })
    let stream = try NativeVadStream(model:"/synthetic",verified:{valid},api:api)
    XCTAssertThrowsError(try [Float](repeating:0,count:7).withUnsafeBufferPointer { try stream.process($0,final:true) })
  }
  func testThirtySecondLimitCannotReachBackendAgain() throws {
    var next = 0, calls = 0, closes = 0
    let api = NativeVadAPI(create: { _ in self.h }, process: { _, pcm, final in
      calls += 1; defer { next += pcm.count }; return self.frame(next,pcm.count,final)
    }, destroy:{_ in closes += 1})
    let stream=try NativeVadStream(model:"/synthetic",verified:{true},api:api)
    let pcm=[Float](repeating:0,count:512)
    for _ in 0..<937 { _ = try pcm.withUnsafeBufferPointer { try stream.process($0,final:false) } }
    XCTAssertThrowsError(try pcm.withUnsafeBufferPointer { try stream.process($0,final:false) })
    XCTAssertEqual(calls,937);XCTAssertEqual(closes,1)
  }
}
