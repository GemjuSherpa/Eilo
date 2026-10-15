import Foundation
#if canImport(CEiloVad)
import CEiloVad
#endif

enum VadFailure: Error { case unavailable }
protocol VadStream: AnyObject {
  func process(_ pcm: UnsafeBufferPointer<Float>, final: Bool) throws -> NativeVadObservation
  func close()
}

struct NativeVadAPI {
  let create: (String) -> OpaquePointer?
  let process: (OpaquePointer, UnsafeBufferPointer<Float>, Bool) -> NativeVadObservation?
  let destroy: (OpaquePointer) -> Void
  static var linked: NativeVadAPI {
    #if canImport(CEiloVad) && DEBUG && EILO_VAD_EVALUATION
    return NativeVadAPI(create: { path in path.withCString { eilo_vad_create($0) } },
      process: { handle, pcm, final in
        var frame = EiloVadFrame()
        guard eilo_vad_process(handle, pcm.baseAddress, Int32(pcm.count), final ? 1 : 0, &frame) == 0 else { return nil }
        return NativeVadObservation(probability: frame.probability, startSample: Int(frame.start_sample),
                                    samples: Int(frame.samples), final: frame.final_frame != 0)
      }, destroy: { eilo_vad_destroy($0) })
    #else
    return NativeVadAPI(create: { _ in nil }, process: { _, _, _ in nil }, destroy: { _ in })
    #endif
  }
}

/// Single inference-worker owner. Verification includes model lease and controller generation;
/// Stop revokes that capability immediately; this owner performs destruction on its worker.
final class NativeVadStream: VadStream {
  private var handle: OpaquePointer?
  private var nextSample = 0
  private let api: NativeVadAPI
  private let verified: () -> Bool
  init(model: String, verified: @escaping () -> Bool, api: NativeVadAPI = .linked) throws {
    self.api = api; self.verified = verified
    guard model.hasPrefix("/"), model.utf8.count <= 4096, !model.utf8.contains(0), verified(),
          let candidate = api.create(model) else { throw VadFailure.unavailable }
    guard verified() else { api.destroy(candidate); throw VadFailure.unavailable }
    handle = candidate
  }
  func process(_ pcm: UnsafeBufferPointer<Float>, final: Bool) throws -> NativeVadObservation {
    guard let current = handle, verified(), (1...512).contains(pcm.count), pcm.count == 512 || final,
          nextSample <= 480000 - pcm.count, pcm.allSatisfy({ $0.isFinite && (-1...1).contains($0) }),
          let frame = api.process(current, pcm, final), verified(),
          frame.probability.isFinite, (0...1).contains(frame.probability), frame.startSample == nextSample,
          frame.samples == pcm.count, frame.final == final else { close(); throw VadFailure.unavailable }
    nextSample += pcm.count
    if final {
      close()
      guard verified() else { throw VadFailure.unavailable }
    }
    return frame
  }
  func close() {
    let old = handle; handle = nil
    if let old { api.destroy(old) }
  }
  deinit { close() }
}
