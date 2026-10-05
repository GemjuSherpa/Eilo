// Native-only test seam. No real adapters or UI/bridge connection.
public protocol CaptureAdapter { func capture() throws -> [Float] }
public protocol AsrAdapter { func transcribe(_ samples: [Float]) throws -> String }
public protocol ModelAdapter { func reply(_ input: String, context: String) throws -> String }
public protocol TtsAdapter { func speak(_ reply: String) throws }
public protocol MemoryAdapter { func eligibleContext() throws -> String }
public enum TurnTestResult: Equatable { case completed, adapterFailed }
public struct TurnTestSeam {
  let capture: any CaptureAdapter
  let asr: any AsrAdapter
  let model: any ModelAdapter
  let tts: any TtsAdapter
  let memory: any MemoryAdapter
  public init(capture: any CaptureAdapter, asr: any AsrAdapter, model: any ModelAdapter,
              tts: any TtsAdapter, memory: any MemoryAdapter) {
    self.capture = capture; self.asr = asr; self.model = model
    self.tts = tts; self.memory = memory
  }
  public func runSyntheticTurn() -> TurnTestResult {
    do {
      var samples = try capture.capture()
      defer { samples = Array(repeating: 0, count: samples.count) }
      let input = try asr.transcribe(samples)
      let context = try memory.eligibleContext()
      let reply = try model.reply(input, context: context)
      try tts.speak(reply)
      return .completed
    } catch {
      // Do not export or log raw exception diagnostics.
      return .adapterFailed
    }
  }
}
