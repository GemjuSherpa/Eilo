import Foundation

enum EndpointResult { case continued, complete, noSpeech, limit, incomplete, invalid }

/// Worker-confined sample clock. Native window scores are never duplicated into 20 ms frames.
final class EndpointDetector {
  private var total = 0, high = 0, quiet = 0
  private(set) var confirmedSpeech = false
  private var terminal = false
  private var nativeMode: Bool?

  func advance(_ probability: Float, samples: Int = 320) -> EndpointResult {
    guard !terminal, nativeMode != true, samples == 320 else { return invalidate() }
    nativeMode = false
    return consume(probability, samples: samples, final: false)
  }

  /// Number of valid samples the next native model call may consume. A shorter-than-512
  /// capacity must be supplied as the model's final padded window, not as extra clock time.
  var nativeInputCapacity: Int {
    guard !terminal, nativeMode != false else { return 0 }
    return min(512, (confirmedSpeech ? 480000 : 80000) - total)
  }

  func advanceNative(_ probability: Float, startSample: Int, samples: Int,
                     final: Bool) -> EndpointResult {
    guard !terminal, nativeMode != false, startSample == total, samples > 0,
          samples <= nativeInputCapacity, samples == 512 || final else { return invalidate() }
    nativeMode = true
    return consume(probability, samples: samples, final: final)
  }

  @discardableResult func invalidate() -> EndpointResult {
    terminal = true
    high = 0; quiet = 0; confirmedSpeech = false
    return .invalid
  }

  private func consume(_ probability: Float, samples: Int, final: Bool) -> EndpointResult {
    guard probability.isFinite, (0...1).contains(probability), total <= 480000 - samples else {
      return invalidate()
    }
    total += samples
    if probability >= 0.8 {
      high += samples; quiet = 0
      if high >= 2560 { confirmedSpeech = true }
    } else if probability <= 0.2 {
      high = 0
      if confirmedSpeech { quiet += samples }
    } else {
      high = 0; quiet = 0
    }
    let result: EndpointResult
    if confirmedSpeech && quiet >= 8000 { result = .complete }
    else if !confirmedSpeech && total >= 80000 { result = .noSpeech }
    else if total >= 480000 { result = .limit }
    else if final { result = .incomplete }
    else { result = .continued }
    terminal = result != .continued
    return result
  }

  var elapsedSamples: Int { total }
}

/// Metadata from one actual native window. Native code owns model selection and verification;
/// this type grants neither confidence nor independent user/echo-separated speech evidence.
struct NativeVadObservation {
  let probability: Float
  let startSample: Int
  let samples: Int
  let final: Bool
}

/// Worker-confined receiver. The owner must include generation cancellation and model-lease
/// validity in verified, and recheck the controller token before applying a returned decision.
final class NativeVadEndpointBridge {
  private let endpoint = EndpointDetector()
  private let verified: () -> Bool
  private var closed = false

  init(verified: @escaping () -> Bool = { false }) { self.verified = verified }
  var inputCapacity: Int {
    guard !closed, verified() else { close(); return 0 }
    return endpoint.nativeInputCapacity
  }
  var elapsedSamples: Int { endpoint.elapsedSamples }

  func consume(_ frame: NativeVadObservation) -> EndpointResult {
    guard !closed, verified() else { close(); return .invalid }
    let result = endpoint.advanceNative(frame.probability, startSample: frame.startSample,
                                      samples: frame.samples, final: frame.final)
    guard verified() else { close(); return .invalid }
    if result != .continued { closed = true }
    return result
  }

  func close() { closed = true; endpoint.invalidate() }
}
