import Foundation

/// Metadata in the normalized 16 kHz clock, never original source-frame indices.
/// The final normalized callback suffix is excluded from totalSamples and erased.
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
  private let sourceRate:Int,frameCapacity:Int
  private var converter:StreamingRateConverter?
  private var storage:[Float]
  private var counts = [Int](repeating: 0, count: 4), times = [UInt64](repeating: 0, count: 4)
  private var head = 0, size = 0, queuedSamples = 0
  private var accepting = true, active = true, scheduled = false, eof = false
  private var failed=false
  private let failure: (@escaping () -> Bool) -> Void
  private var lastClock: UInt64?
  // Worker-only fields. Stop never touches these or waits for inference.
  private let audioFactory:(()->VadAsrHandoff)?
  private let joinedOutput:((VadCaptureOutcome,AsrText?,@escaping ()->Bool)->Void)?
  private var audio:VadAsrHandoff?
  private var delivery: VadWindowDelivery?
  private var scratch:[Float]
  init(schedule: @escaping (@escaping () -> Void) -> Void, verified: @escaping () -> Bool = { false },
       open: @escaping () throws -> VadStream = { throw VadFailure.unavailable },
       now: @escaping () -> UInt64 = { DispatchTime.now().uptimeNanoseconds },
       output: @escaping (VadCaptureOutcome, @escaping () -> Bool) -> Void = { _,_ in },
       failure: @escaping (@escaping () -> Bool) -> Void = { _ in },
       audioFactory:(()->VadAsrHandoff)?=nil,
       joinedOutput:((VadCaptureOutcome,AsrText?,@escaping ()->Bool)->Void)?=nil,sourceRate:Int=16000) {
    self.sourceRate=sourceRate;frameCapacity=sourceRate==48000 ? 4800:1600
    storage=[Float](repeating:0,count:frameCapacity*4);scratch=[Float](repeating:0,count:frameCapacity)
    self.audioFactory=audioFactory;self.joinedOutput=joinedOutput;self.failure=failure; self.schedule=schedule; self.verified=verified; self.open=open; self.now=now; self.output=output
  }
  /// Queued raw source samples; excludes worker FIR/VAD/ASR state.
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
    let valid=(sourceRate==16000 || sourceRate==48000) && sampleRate==sourceRate && (1...frameCapacity).contains(pcm.count) && size<4 &&
      pcm.allSatisfy({ $0.isFinite && (-1...1).contains($0) }) &&
      (lastClock == nil || time >= lastClock!) &&
      (size==0 || (time>=times[head] && time-times[head]<250_000_000))
    if valid {
      let slot=(head+size)%4
      for i in pcm.indices { storage[slot*frameCapacity+i]=pcm[i] }
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
      let count=counts[head],offset=head*frameCapacity
      for i in 0..<count { scratch[i]=storage[offset+i]; storage[offset+i]=0 }
      counts[head]=0; times[head]=0; head=(head+1)%4; size-=1; queuedSamples-=count
      lock.unlock()
      if delivery == nil { delivery=VadWindowDelivery(allowed:{ [weak self] in self?.allowed() ?? false },open:open) }
      var event=VadDeliveryEvent(result:.continued,consumedSamples:0)
      do {
        guard allowed() else{throw VadFailure.unavailable}
        if converter == nil {converter=try StreamingRateConverter(sourceRate:sourceRate)}
        try scratch.withUnsafeBufferPointer {raw in
          try converter!.convert(UnsafeBufferPointer(rebasing:raw[0..<count])){normalized in
            guard allowed() else{throw VadFailure.unavailable}
            event=delivery!.accept(normalized,startSample:delivery!.acceptedSamples)
            if event.result != .invalid,allowed(),let factory=audioFactory {
              if audio == nil {audio=factory()}
              let start=(delivery?.acceptedSamples ?? 0)-event.consumedSamples
              if !audio!.append(normalized,consumed:event.consumedSamples,startSample:start){throw VadFailure.unavailable}
            }
          }
        }
        if !allowed(){throw VadFailure.unavailable}
      } catch {event=VadDeliveryEvent(result:.invalid,consumedSamples:0)}
      scratch.withUnsafeMutableBufferPointer { $0.initialize(repeating:0) }
      if event.result != .continued { complete(event); return }
    }
  }
  private func complete(_ event: VadDeliveryEvent) {
    let outcome=VadCaptureOutcome(result:event.result,totalSamples:delivery?.acceptedSamples ?? 0,lastChunkConsumed:event.consumedSamples)
    var text:AsrText?,invalid=event.result == .invalid
    if !invalid,let factory=audioFactory {
      if audio == nil {audio=factory()}
      switch audio!.finish(outcome) {
      case .metadata:break
      case .recognized(let final):text=final
      case .invalid:invalid=true
      }
    }
    cleanup()
    lock.lock(); accepting=false; clearLocked(); scheduled=false
    if invalid { if active { failed=true }; active=false }
    lock.unlock()
    if invalid { reportFailure() }
    else if allowed() {
      let current={ [weak self] in self?.allowed() ?? false }
      if let joinedOutput {joinedOutput(outcome,text,current)}else{output(outcome,current)}
    }
  }
  private func failureCurrent() -> Bool { lock.lock(); defer { lock.unlock() }; return failed }
  private func reportFailure() { if failureCurrent() { failure { [weak self] in self?.failureCurrent() ?? false } } }
  private func cleanup() {
    scratch.withUnsafeMutableBufferPointer { $0.initialize(repeating:0) }
    delivery?.close(); delivery=nil;audio?.close();audio=nil;converter?.close();converter=nil
  }
}
