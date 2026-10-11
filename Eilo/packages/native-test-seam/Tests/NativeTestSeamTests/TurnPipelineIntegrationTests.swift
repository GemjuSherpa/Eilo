import XCTest
@testable import NativeTestSeam

/// Scripted native integration; no acoustic recognition or production capture attachment.
final class TurnPipelineIntegrationTests: XCTestCase {
  final class Backend: AsrStream {
    var received = [Float](), closes = 0
    var onFinal: () -> Void = {}
    func accept(_ pcm: UnsafeBufferPointer<Float>) throws { received += Array(pcm) }
    func text(finish: Bool) throws -> String { if finish { onFinal() }; return "What time is it?" }
    func close() { closes += 1 }
  }

  func testBoundedSuffixAndDuplicatesProduceOneFinalThenUnscoredTextClarifies() {
    let effects = EffectsSpy(), controller = testController(effects: effects)
    XCTAssertTrue(controller.dispatch(.start))
    let handoff = WakeQuestionHandoff()
    for frame in 0..<14 {
      let pcm = [Float](repeating: frame < 2 ? -0.5 : 0.5, count: 320)
      XCTAssertTrue(pcm.withUnsafeBufferPointer { handoff.offer($0, startSample: UInt64(frame * 320)) })
    }
    XCTAssertTrue(controller.dispatch(.speechDetected, token: controller.token))
    let token = controller.token!, backend = Backend(), endpoint = EndpointDetector()
    let asr = StreamingAsr(token, allowed: { controller.recognitionAllowed(token) }, open: { backend })
    var final: AsrText?
    XCTAssertTrue(handoff.activate(token, firstQuestionSample: 640, allowed: { controller.recognitionAllowed(token) }, consume: { pcm in
      for offset in stride(from: 0, to: pcm.count, by: 320) {
        let frame = UnsafeBufferPointer(rebasing: pcm[offset..<(offset + 320)])
        XCTAssertTrue(asr.accept(frame))
        // Known synthetic markers supply scripted VAD probabilities only in this test.
        if endpoint.advance(frame[0] == 0 ? 0.1 : 0.95) == .complete { final = asr.poll(finish: true) }
      }
    }))
    XCTAssertEqual(backend.received.count, 3840)
    for frame in 14..<22 {
      XCTAssertTrue([Float](repeating: 0.5, count: 320).withUnsafeBufferPointer { handoff.offer($0, startSample: UInt64(frame * 320)) })
    }
    XCTAssertTrue([Float](repeating: 0.5, count: 320).withUnsafeBufferPointer { handoff.offer($0, startSample: 21 * 320) })
    XCTAssertEqual(backend.received.count, 6400)
    for frame in 22..<47 {
      XCTAssertTrue([Float](repeating: 0, count: 320).withUnsafeBufferPointer { handoff.offer($0, startSample: UInt64(frame * 320)) })
    }
    XCTAssertEqual(backend.received.count, 14400)
    XCTAssertTrue(backend.received.prefix(6400).allSatisfy { $0 == 0.5 })
    XCTAssertTrue(backend.received.dropFirst(6400).allSatisfy { $0 == 0 })
    XCTAssertEqual(final?.text, "What time is it?")
    XCTAssertEqual(backend.closes, 1)
    XCTAssertNil(asr.poll(finish: true))
    XCTAssertTrue(controller.finishRecognition(token, result: final!, confidence: nil, active: { true }, accepted: { _ in XCTFail("Unscored text must not reach conversation processing") }))
    XCTAssertEqual(effects.clauses, [RecognitionPolicy.clarification])
    handoff.close()
    XCTAssertEqual(handoff.retainedSamples, 0)
  }

  func testStopAndReplacementDuringBackendFinalRejectOldText() {
    let controller = testController()
    XCTAssertTrue(controller.dispatch(.start))
    XCTAssertTrue(controller.dispatch(.speechDetected, token: controller.token))
    let token = controller.token!, backend = Backend()
    let asr = StreamingAsr(token, allowed: { controller.recognitionAllowed(token) }, open: { backend })
    XCTAssertTrue([Float](repeating: 0, count: 320).withUnsafeBufferPointer { asr.accept($0) })
    backend.onFinal = { controller.stop(); _ = controller.dispatch(.start) }
    XCTAssertNil(asr.poll(finish: true))
    XCTAssertTrue(token.cancelled)
    XCTAssertEqual(controller.state, .standby)
    XCTAssertEqual(backend.closes, 1)
  }
}
