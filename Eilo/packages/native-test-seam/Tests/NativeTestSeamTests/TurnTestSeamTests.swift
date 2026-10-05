import XCTest
@testable import NativeTestSeam
final class TurnTestSeamTests: XCTestCase {
  final class Fakes: CaptureAdapter, AsrAdapter, ModelAdapter, TtsAdapter, MemoryAdapter {
    var calls: [String] = []
    var failAsr = false
    enum Failure: Error { case synthetic }
    func capture() -> [Float] { calls.append("capture"); return [0.25] }
    func transcribe(_ samples: [Float]) throws -> String {
      calls.append("asr"); XCTAssertEqual(samples, [0.25])
      if failAsr { throw Failure.synthetic }
      return "synthetic hello"
    }
    func eligibleContext() -> String { calls.append("memory"); return "" }
    func reply(_ input: String, context: String) -> String {
      calls.append("model"); XCTAssertEqual(input, "synthetic hello"); XCTAssertEqual(context, "")
      return "synthetic reply"
    }
    func speak(_ reply: String) { calls.append("tts"); XCTAssertEqual(reply, "synthetic reply") }
  }
  func testSyntheticTurnUsesOnlyInjectedFakes() {
    let fake = Fakes()
    let seam = TurnTestSeam(capture: fake, asr: fake, model: fake, tts: fake, memory: fake)
    XCTAssertEqual(seam.runSyntheticTurn(), .completed)
    XCTAssertEqual(fake.calls, ["capture", "asr", "memory", "model", "tts"])
  }
  func testFailureStopsDownstreamWork() {
    let fake = Fakes(); fake.failAsr = true
    let seam = TurnTestSeam(capture: fake, asr: fake, model: fake, tts: fake, memory: fake)
    XCTAssertEqual(seam.runSyntheticTurn(), .adapterFailed)
    XCTAssertEqual(fake.calls, ["capture", "asr"])
  }
}
