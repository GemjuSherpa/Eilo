import Foundation
@main struct DefaultLlmBindingEvaluation {
  static func main() {
    do {
      let stream = try NativeLlmStream(allowed: { true })
      stream.close(); exit(1)
    } catch LlmFailure.unavailable {
      print("DEFAULT_UNAVAILABLE\tPASS")
    } catch { exit(1) }
  }
}
