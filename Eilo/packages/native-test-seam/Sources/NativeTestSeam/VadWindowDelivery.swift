import Foundation

struct VadDeliveryEvent {
  let result: EndpointResult
  let consumedSamples: Int
}

/// Single native inference-worker owner. Capture callbacks must enqueue/copy elsewhere;
/// this class never schedules work, blocks a controller, or retains a borrowed input pointer.
final class VadWindowDelivery {
  private let allowed: () -> Bool
  private let open: () throws -> VadStream
  private let endpoint: NativeVadEndpointBridge
  private var stream: VadStream?
  private var scratch = [Float](repeating: 0, count: 512)
  private var pending = 0, inputSamples = 0
  private var closed = false

  init(allowed: @escaping () -> Bool = { false }, open: @escaping () throws -> VadStream = { throw VadFailure.unavailable }) {
    self.allowed = allowed; self.open = open
    endpoint = NativeVadEndpointBridge(verified: allowed)
  }
  var retainedSamples: Int { pending }
  var acceptedSamples: Int { inputSamples }
  private func clear() { scratch.withUnsafeMutableBufferPointer { $0.initialize(repeating: 0) }; pending = 0 }
  private func invalid() -> VadDeliveryEvent { close(); return VadDeliveryEvent(result: .invalid, consumedSamples: 0) }

  func accept(_ pcm: UnsafeBufferPointer<Float>, startSample: Int) -> VadDeliveryEvent {
    guard !closed, allowed(), startSample == inputSamples, (1...1600).contains(pcm.count),
          pcm.allSatisfy({ $0.isFinite && (-1...1).contains($0) }) else { return invalid() }
    var offset = 0
    while offset < pcm.count {
      let capacity = endpoint.inputCapacity
      guard allowed(), capacity > pending else { return invalid() }
      let take = min(capacity - pending, pcm.count - offset)
      for i in 0..<take { scratch[pending + i] = pcm[offset + i] }
      pending += take; inputSamples += take; offset += take
      guard allowed() else { return invalid() }
      if pending == capacity {
        guard let result = process(final: capacity < 512) else { return invalid() }
        if result != .continued { return finishEvent(result, consumed: offset) }
      }
    }
    guard allowed() else { return invalid() }
    return VadDeliveryEvent(result: .continued, consumedSamples: offset)
  }

  /// EOF does not create extra zero-time evidence. Empty pending data needs no extra model call.
  func finish() -> VadDeliveryEvent {
    guard !closed, allowed() else { return invalid() }
    if pending == 0 { return finishEvent(.incomplete, consumed: 0) }
    guard let result = process(final: true) else { return invalid() }
    return finishEvent(result, consumed: 0)
  }

  private func process(final: Bool) -> EndpointResult? {
    defer { clear() }
    do {
      guard allowed() else { return nil }
      if stream == nil {
        let candidate = try open()
        guard allowed() else { candidate.close(); return nil }
        stream = candidate
      }
      guard let current = stream, allowed() else { return nil }
      let expected = pending, start = endpoint.elapsedSamples
      let frame = try scratch.withUnsafeBufferPointer {
        try current.process(UnsafeBufferPointer(rebasing: $0[0..<expected]), final: final)
      }
      guard !closed, allowed(), frame.startSample == start, frame.samples == expected, frame.final == final else { return nil }
      return endpoint.consume(frame)
    } catch { return nil }
  }
  private func finishEvent(_ result: EndpointResult, consumed: Int) -> VadDeliveryEvent {
    close()
    guard allowed(), result != .continued else { return VadDeliveryEvent(result: .invalid, consumedSamples: 0) }
    return VadDeliveryEvent(result: result, consumedSamples: result == .invalid ? 0 : consumed)
  }
  func close() {
    guard !closed else { return }
    closed = true
    let previous = stream; stream = nil
    clear(); endpoint.close(); previous?.close()
  }
  deinit { close() }
}
