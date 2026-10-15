import XCTest
@testable import NativeTestSeam

final class NativeEndpointTests: XCTestCase {
  func testNativeSpeechUsesFiveActualWindowsAndSilenceNeverEndsEarly() {
    let d = EndpointDetector()
    for i in 0..<4 {
      XCTAssertEqual(d.advanceNative(0.95, startSample: i * 512, samples: 512, final: false), .continued)
      XCTAssertFalse(d.confirmedSpeech)
    }
    XCTAssertEqual(d.advanceNative(0.95, startSample: 2048, samples: 512, final: false), .continued)
    XCTAssertTrue(d.confirmedSpeech)
    for i in 0..<15 {
      XCTAssertEqual(d.advanceNative(0.05, startSample: 2560 + i * 512, samples: 512, final: false), .continued)
    }
    XCTAssertEqual(d.advanceNative(0.05, startSample: 10240, samples: 512, final: false), .complete)
    XCTAssertEqual(d.elapsedSamples, 10752) // 160 ms speech + 512 ms observed silence.
    XCTAssertEqual(d.nativeInputCapacity, 0)
  }

  func testFiveSecondBudgetRequiresValidPartialFinalWindow() {
    let d = EndpointDetector()
    for i in 0..<156 { XCTAssertEqual(d.advanceNative(0.05, startSample: i * 512, samples: 512, final: false), .continued) }
    XCTAssertEqual(d.nativeInputCapacity, 128)
    XCTAssertEqual(d.advanceNative(0.05, startSample: 79872, samples: 128, final: true), .noSpeech)
    XCTAssertEqual(d.elapsedSamples, 80000)
    XCTAssertFalse(d.confirmedSpeech)
    let overshoot = EndpointDetector()
    for i in 0..<156 { _ = overshoot.advanceNative(0.05, startSample: i * 512, samples: 512, final: false) }
    XCTAssertEqual(overshoot.advanceNative(0.05, startSample: 79872, samples: 512, final: false), .invalid)
    XCTAssertEqual(overshoot.elapsedSamples, 79872)
  }

  func testThirtySecondsAndEofCannotCountPaddingOrInventCompletion() {
    let d = EndpointDetector()
    for i in 0..<937 { XCTAssertEqual(d.advanceNative(0.95, startSample: i * 512, samples: 512, final: false), .continued) }
    XCTAssertEqual(d.nativeInputCapacity, 256)
    XCTAssertEqual(d.advanceNative(0.95, startSample: 479744, samples: 256, final: true), .limit)
    XCTAssertEqual(d.elapsedSamples, 480000)
    let eof = EndpointDetector()
    XCTAssertEqual(eof.advanceNative(0.95, startSample: 0, samples: 7, final: true), .incomplete)
    XCTAssertEqual(eof.elapsedSamples, 7)
    XCTAssertFalse(eof.confirmedSpeech)
    XCTAssertEqual(eof.advanceNative(0.95, startSample: 7, samples: 512, final: false), .invalid)
  }

  func testDiscontinuityFrameShapeAndMixedClocksRevokePermanently() {
    for (start, count, final) in [(1,512,false),(0,0,true),(0,513,true),(0,128,false),(-1,512,false)] {
      let d = EndpointDetector()
      XCTAssertEqual(d.advanceNative(0.9, startSample: start, samples: count, final: final), .invalid)
      XCTAssertEqual(d.nativeInputCapacity, 0)
    }
    let duplicate = EndpointDetector()
    _ = duplicate.advanceNative(0.9, startSample: 0, samples: 512, final: false)
    XCTAssertEqual(duplicate.advanceNative(0.9, startSample: 0, samples: 512, final: false), .invalid)
    XCTAssertEqual(duplicate.elapsedSamples, 512)
    let legacy = EndpointDetector(); _ = legacy.advance(0.9)
    XCTAssertEqual(legacy.advanceNative(0.9, startSample: 320, samples: 512, final: false), .invalid)
    let native = EndpointDetector(); _ = native.advanceNative(0.9, startSample: 0, samples: 512, final: false)
    XCTAssertEqual(native.advance(0.9), .invalid)
    XCTAssertFalse(native.confirmedSpeech)
  }

  func testUnknownResetsSilenceAndShortHighRunsDoNotConfirmSpeech() {
    let d = EndpointDetector()
    for i in 0..<5 { _ = d.advanceNative(0.9, startSample: i * 512, samples: 512, final: false) }
    for _ in 0..<15 { _ = d.advanceNative(0.1, startSample: d.elapsedSamples, samples: 512, final: false) }
    _ = d.advanceNative(0.5, startSample: d.elapsedSamples, samples: 512, final: false)
    for _ in 0..<15 { XCTAssertEqual(d.advanceNative(0.1, startSample: d.elapsedSamples, samples: 512, final: false), .continued) }
    XCTAssertEqual(d.advanceNative(0.1, startSample: d.elapsedSamples, samples: 512, final: false), .complete)
    let burst = EndpointDetector()
    for i in 0..<4 { _ = burst.advanceNative(0.9, startSample: i * 512, samples: 512, final: false) }
    _ = burst.advanceNative(0.5, startSample: 2048, samples: 512, final: false)
    _ = burst.advanceNative(0.9, startSample: 2560, samples: 512, final: false)
    XCTAssertFalse(burst.confirmedSpeech)
  }

  func testInvalidProbabilityDoesNotAdvanceAndClearsEvidence() {
    for p: Float in [.nan, .infinity, -0.1, 1.1] {
      let d = EndpointDetector()
      XCTAssertEqual(d.advanceNative(p, startSample: 0, samples: 512, final: false), .invalid)
      XCTAssertEqual(d.elapsedSamples, 0)
    }
  }

  func testDefaultDeniedAndRevocationBetweenChecksCannotReleaseDecision() {
    let frame = NativeVadObservation(probability: 0.9, startSample: 0, samples: 512, final: false)
    let unavailable = NativeVadEndpointBridge()
    XCTAssertEqual(unavailable.consume(frame), .invalid)
    XCTAssertEqual(unavailable.elapsedSamples, 0)
    var calls = 0
    let revoked = NativeVadEndpointBridge(verified: { calls += 1; return calls == 1 })
    XCTAssertEqual(revoked.consume(frame), .invalid)
    XCTAssertEqual(revoked.inputCapacity, 0)
    XCTAssertEqual(revoked.consume(frame), .invalid)
    XCTAssertEqual(calls, 2)
  }

  func testBridgeCloseAndFinalAreTerminal() {
    let b = NativeVadEndpointBridge(verified: { true })
    XCTAssertEqual(b.consume(NativeVadObservation(probability: 0.1, startSample: 0, samples: 5, final: true)), .incomplete)
    XCTAssertEqual(b.inputCapacity, 0)
    b.close(); b.close()
    XCTAssertEqual(b.consume(NativeVadObservation(probability: 0.9, startSample: 5, samples: 512, final: false)), .invalid)
  }
  func testCapacityRequestCannotOpenOrReviveARevokedLease() {
    XCTAssertEqual(NativeVadEndpointBridge().inputCapacity, 0)
    var valid = true
    let b = NativeVadEndpointBridge(verified: { valid })
    XCTAssertEqual(b.inputCapacity, 512)
    valid = false
    XCTAssertEqual(b.inputCapacity, 0)
    valid = true
    XCTAssertEqual(b.inputCapacity, 0)
  }

  func testRevocationAtCompletedEndpointWithholdsTheDecision() {
    var checks = 0
    let b = NativeVadEndpointBridge(verified: { checks += 1; return checks < 42 })
    for i in 0..<20 {
      XCTAssertEqual(b.consume(NativeVadObservation(probability: i < 5 ? 0.9 : 0.1,
        startSample: i * 512, samples: 512, final: false)), .continued)
    }
    XCTAssertEqual(b.consume(NativeVadObservation(probability: 0.1, startSample: 10240,
      samples: 512, final: false)), .invalid)
    XCTAssertEqual(b.inputCapacity, 0)
  }

}
