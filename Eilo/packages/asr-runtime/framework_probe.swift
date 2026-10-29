import Foundation
import CEiloAsr
import CEiloLlm

private struct FrameworkPermission: MicrophonePermissionAdapter {
  func status() -> MicrophonePermission { .granted }
  func request(_ completion: @escaping (MicrophonePermission) -> Void) { completion(.granted) }
}
private struct FrameworkModels: ModelReadinessAdapter { func status() -> ModelStatus { .ready } }
private final class FrameworkEffects: ControllerEffects {
  func startCapture() -> Bool { true }
  func playClause(_ clause: String) throws {}
  func cancelWork() throws {}
  func releaseCapture() throws {}
  func clearVolatileContext() throws {}
}
@main struct FrameworkProbe {
  static func main() throws {
    guard CommandLine.arguments.count == 3, let llm = eilo_llm_create() else { throw AsrFailure.unavailable }
    defer { eilo_llm_destroy(llm) }
    // Real statically linked LLM code coexists with the ASR framework. No model
    // load, generation, microphone, speech SDK or production readiness is enabled.
    eilo_llm_cancel(llm)
    let denied = "test".withCString { eilo_llm_count_tokens(llm, $0, 4) < 0 }
    guard denied else { throw AsrFailure.unavailable }
    let data = try Data(contentsOf: URL(fileURLWithPath: CommandLine.arguments[2]))
    guard !data.isEmpty, data.count % 4 == 0, data.count <= 480000 * 4 else { throw AsrFailure.unavailable }
    var pcm = data.withUnsafeBytes { Array($0.bindMemory(to: Float.self)) }
    let controller = NativeController(effects: FrameworkEffects(), permission: FrameworkPermission(), models: FrameworkModels())
    guard controller.dispatch(.start), controller.dispatch(.speechDetected, token: controller.token), let token = controller.token else { throw AsrFailure.unavailable }
    let stream = StreamingAsr(token, allowed: { !token.cancelled }, open: {
      try NativeAsrStream(directory: CommandLine.arguments[1], verified: { true })
    })
    for i in stride(from: 0, to: pcm.count, by: 320) {
      let end = min(i + 320, pcm.count)
      guard pcm.withUnsafeBufferPointer({ stream.accept(UnsafeBufferPointer(rebasing: $0[i..<end])) }) else { throw AsrFailure.unavailable }
    }
    pcm.withUnsafeMutableBufferPointer { $0.initialize(repeating: 0) }
    guard let final = stream.poll(finish: true), final.final, !final.text.isEmpty, stream.poll(finish: true) == nil else { throw AsrFailure.unavailable }
    let canceled = StreamingAsr(token, allowed: { !token.cancelled }, open: {
      try NativeAsrStream(directory: CommandLine.arguments[1], verified: { true })
    })
    guard [Float](repeating: 0, count: 320).withUnsafeBufferPointer({ canceled.accept($0) }) else { throw AsrFailure.unavailable }
    controller.stop()
    guard canceled.poll(finish: true) == nil else { throw AsrFailure.unavailable }
    let result: [String: Any] = ["framework_asr_final": true, "duplicate_final_rejected": true,
      "stale_final_rejected": true, "linked_llm_unloaded_gate_rejected": true,
      "microphone": "NOT_OPENED", "llm_generation": "NOT_RUN", "physical": "NOT_RUN"]
    let encoded = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
    print("EILO_FRAMEWORK_RESULT\t" + String(decoding: encoded, as: UTF8.self))
  }
}
