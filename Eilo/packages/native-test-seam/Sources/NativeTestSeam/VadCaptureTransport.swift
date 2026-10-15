import Foundation

/// Metadata only. The final callback's suffix is excluded from totalSamples and erased.
struct VadCaptureOutcome {
  let result: EndpointResult
  let totalSamples: Int
  let lastChunkConsumed: Int
}

/// Four copied 100 ms frames maximum, <250 ms queue age, one coalesced worker job.
/// schedule MUST enqueue on one dedicated serial inference worker, never inline/on capture.
/// verified is a disk-free capability check; it must not acquire capture/controller locks.
final class VadCaptureTransport: @unchecked Sendable {
  private let lock = NSLock()
  private let schedule: (@escaping () -> Void) -> Void
  private let verified: () -> Bool
  private let open: () throws -> VadStream
  private let output: (VadCaptureOutcome, @escaping () -> Bool) -> Void
  private let now: () -> UInt64
  private var storage = [Float](repeating: 0, count: 6400)
  private var counts = [Int](repeating: 0, count: 4), times = [UInt64](repeating: 0, count: 4)
  private var head = 0, size = 0, queuedSamples = 0
  private var accepting = true, active = true, scheduled = false, eof = false
  private var failed=false
  private let failure: (@escaping () -> Bool) -> Void
  private var lastClock: UInt64?
  // Worker-only fields. Stop never touches these or waits for inference.
  private var delivery: VadWindowDelivery?
  private var scratch = [Float](repeating: 0, count: 1600)
  init(schedule: @escaping (@escaping () -> Void) -> Void, verified: @escaping () -> Bool = { false },
       open: @escaping () throws -> VadStream = { throw VadFailure.unavailable },
       now: @escaping () -> UInt64 = { DispatchTime.now().uptimeNanoseconds },
       output: @escaping (VadCaptureOutcome, @escaping () -> Bool) -> Void = { _,_ in },
       failure: @escaping (@escaping () -> Bool) -> Void = { _ in }) {
    self.failure=failure; self.schedule=schedule; self.verified=verified; self.open=open; self.now=now; self.output=output
  }
  var retainedSamples: Int { lock.lock(); defer { lock.unlock() }; return queuedSamples }
  func current() -> Bool { lock.lock(); defer { lock.unlock() }; return active }
  private func clearLocked() {
    storage.withUnsafeMutableBufferPointer { $0.initialize(repeating: 0) }
    counts = [Int](repeating: 0, count: 4); times = [UInt64](repeating: 0, count: 4)
    head=0; size=0; queuedSamples=0
  }
  private func revokeLocked() { failed=true; active=false; accepting=false; clearLocked() }
  private func claimLocked() -> Bool { if scheduled { return false }; scheduled=true; return true }
  @discardableResult func submit(_ pcm: UnsafeBufferPointer<Float>, sampleRate: Int) -> Bool {
    lock.lock()
    guard accepting else { lock.unlock(); return false }
    let time=now()
    let valid=sampleRate==16000 && (1...1600).contains(pcm.count) && size<4 &&
      pcm.allSatisfy({ $0.isFinite && (-1...1).contains($0) }) &&
      (lastClock == nil || time >= lastClock!) &&
      (size==0 || (time>=times[head] && time-times[head]<250_000_000))
    if valid {
      let slot=(head+size)%4
      for i in pcm.indices { storage[slot*1600+i]=pcm[i] }
      counts[slot]=pcm.count; times[slot]=time; size+=1; queuedSamples+=pcm.count; lastClock=time
    } else { revokeLocked() }
    let start=claimLocked(); lock.unlock()
    if start { schedule { [self] in drain() } }
    return valid
  }
  /// EOF is ordered after queued frames; it never inserts padded clock time.
  func finish() {
    lock.lock(); guard accepting else { lock.unlock(); return }
    accepting=false; eof=true; let start=claimLocked(); lock.unlock()
    if start { schedule { [self] in drain() } }
  }
  /// Immediate revoke/queue erasure; native scratch/state cleanup is always worker-owned.
  func close() {
    lock.lock(); revokeLocked(); failed=false; let start=claimLocked(); lock.unlock()
    if start { schedule { [self] in drain() } }
  }
  private func allowed() -> Bool { current() && verified() && current() }
  private func drain() {
    while true {
      lock.lock()
      if !active {
        clearLocked(); lock.unlock(); cleanup(); lock.lock(); scheduled=false; lock.unlock(); reportFailure(); return
      }
      if size==0 {
        let final=eof
        if !final { scheduled=false; lock.unlock(); return }
        lock.unlock()
        if delivery == nil { delivery=VadWindowDelivery(allowed:{ [weak self] in self?.allowed() ?? false },open:open) }
        let event=delivery!.finish(); complete(event); return
      }
      let time=now()
      guard time>=times[head],time-times[head]<250_000_000,lastClock == nil || time>=lastClock! else {
        revokeLocked(); lock.unlock(); continue
      }
      lastClock=time
      let count=counts[head],offset=head*1600
      for i in 0..<count { scratch[i]=storage[offset+i]; storage[offset+i]=0 }
      counts[head]=0; times[head]=0; head=(head+1)%4; size-=1; queuedSamples-=count
      lock.unlock()
      if delivery == nil { delivery=VadWindowDelivery(allowed:{ [weak self] in self?.allowed() ?? false },open:open) }
      let event=scratch.withUnsafeBufferPointer { delivery!.accept(UnsafeBufferPointer(rebasing:$0[0..<count]), startSample:delivery!.acceptedSamples) }
      scratch.withUnsafeMutableBufferPointer { $0.initialize(repeating:0) }
      if event.result != .continued { complete(event); return }
    }
  }
  private func complete(_ event: VadDeliveryEvent) {
    let outcome=VadCaptureOutcome(result:event.result,totalSamples:delivery?.acceptedSamples ?? 0,lastChunkConsumed:event.consumedSamples)
    cleanup()
    lock.lock(); accepting=false; clearLocked(); scheduled=false
    if event.result == .invalid { if active { failed=true }; active=false }
    lock.unlock()
    if event.result == .invalid { reportFailure() }
    else if allowed() { output(outcome,{ [weak self] in self?.allowed() ?? false }) }
  }
  private func failureCurrent() -> Bool { lock.lock(); defer { lock.unlock() }; return failed }
  private func reportFailure() { if failureCurrent() { failure { [weak self] in self?.failureCurrent() ?? false } } }
  private func cleanup() {
    scratch.withUnsafeMutableBufferPointer { $0.initialize(repeating:0) }
    delivery?.close(); delivery=nil
  }
}
