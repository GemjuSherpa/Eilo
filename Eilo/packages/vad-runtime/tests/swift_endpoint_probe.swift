import Foundation
import CEiloVad

@main struct NativeEndpointProbe {
  static func require(_ value: Bool) {
    if !value { exit(2) }
  }
  static func main() {
    require(CommandLine.arguments.count == 2)
    let model = CommandLine.arguments[1]
    guard let handle = model.withCString({ eilo_vad_create($0) }) else { exit(3) }
    defer { eilo_vad_destroy(handle) }
    // The caller verified the exact file/runtime before this synthetic invocation. This
    // closure does not represent a production signed-pack or controller capability.
    let bridge = NativeVadEndpointBridge(verified: { true })
    var result = EndpointResult.continued
    var windows = 0
    while result == .continued {
      let count = bridge.inputCapacity
      require(count > 0)
      var pcm = [Float](repeating: 0, count: count)
      var frame = EiloVadFrame()
      let code = pcm.withUnsafeBufferPointer {
        eilo_vad_process(handle, $0.baseAddress, Int32(count), count < 512 ? 1 : 0, &frame)
      }
      pcm.withUnsafeMutableBufferPointer { $0.initialize(repeating: 0) }
      require(code == 0)
      result = bridge.consume(NativeVadObservation(probability: frame.probability,
        startSample: Int(frame.start_sample), samples: Int(frame.samples), final: frame.final_frame != 0))
      windows += 1
    }
    require(result == .noSpeech && bridge.elapsedSamples == 80000 && windows == 157)
    require(bridge.inputCapacity == 0)
    var checks = 0
    let revoked = NativeVadEndpointBridge(verified: { checks += 1; return checks == 1 })
    require(revoked.consume(NativeVadObservation(probability: 0.1, startSample: 0, samples: 512, final: false)) == .invalid)
    require(revoked.inputCapacity == 0)
    print("{\"scope\":\"SYNTHETIC_NATIVE_VAD_TO_SWIFT_ENDPOINT\",\"windows\":157,\"valid_samples\":80000,\"result\":\"NO_SPEECH\",\"revocation_rejected\":true,\"physical\":\"NOT_RUN\"}")
  }
}
