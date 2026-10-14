import Foundation

/// Exclusively owned native bytes. No Array/Data COW alias survives construction.
/// Caller clears its source; ownership transfers once to submit, including rejection.
final class LlmOwnedPrompt {
  private let lock = NSLock()
  private let bytes: UnsafeMutablePointer<UInt8>
  let count: Int
  private var claimed = false, borrowed = false, cancelled = false
  init(_ input: UnsafeBufferPointer<UInt8>) throws {
    guard (1...16384).contains(input.count), !input.contains(0) else { throw LlmFailure.unavailable }
    count = input.count; bytes = .allocate(capacity: count); bytes.initialize(from: input.baseAddress!, count: count)
  }
  func claim() -> Bool { lock.lock(); defer { lock.unlock() }; guard !claimed, !cancelled else { return false }; claimed = true; return true }
  func cancel() { lock.lock(); defer { lock.unlock() }; cancelled = true; if !borrowed { bytes.update(repeating: 0, count: count) } }
  func withBorrow(_ use: (UnsafeBufferPointer<UInt8>) throws -> Void) throws {
    lock.lock(); guard claimed, !cancelled, !borrowed else { lock.unlock(); throw LlmFailure.cancelled }
    borrowed = true; lock.unlock()
    defer { lock.lock(); bytes.update(repeating: 0, count: count); borrowed = false; cancelled = true; lock.unlock() }
    try use(UnsafeBufferPointer(start: bytes, count: count))
  }
  var cleared: Bool { lock.lock(); defer { lock.unlock() }; return !borrowed && UnsafeBufferPointer(start: bytes, count: count).allSatisfy { $0 == 0 } }
  deinit { bytes.update(repeating: 0, count: count); bytes.deinitialize(count: count); bytes.deallocate() }
}
enum LlmJobResult { case completed, cancelled, unavailable }
final class LlmWorkTicket {
  weak var controller: NativeController?
  let token: GenerationToken, cancel: () -> Void
  private let lock = NSLock()
  private var revoked = false
  var cancelled: Bool { get { lock.lock(); defer { lock.unlock() }; return revoked }
    set { lock.lock(); revoked = newValue; lock.unlock() } }
  init(controller: NativeController, token: GenerationToken, cancel: @escaping () -> Void) {
    self.controller = controller; self.token = token; self.cancel = cancel
  }
}
/// One separate native worker owns resolve/hash/load/prefill/decode/close.
/// Only cancellation is concurrent. Await cleanup off UI/controller/capture threads.
/// Raw consumers perform bounded native buffer work and gain no speech rights.
final class LlmControllerJob {
  private let controller: NativeController, prompt: LlmOwnedPrompt
  private let completion:(LlmJobResult)->Void,request:GenericReplyRequest?
  private let gate = NSCondition()
  private var cancelled = false, stream: NativeLlmStream?, result: LlmJobResult?, workerThread: Thread?
  private static let worker = DispatchQueue(label: "com.eilo.llm.worker")
  private init(controller: NativeController, prompt: LlmOwnedPrompt, completion:@escaping(LlmJobResult)->Void,request:GenericReplyRequest?) { self.controller = controller; self.prompt = prompt;self.completion=completion;self.request=request }
  func requestCancellation() {
    request?.cancel();prompt.cancel()
    gate.lock(); cancelled = true; let current = stream; gate.unlock()
    current?.requestCancellation()
  }
  func awaitCompletion(timeout: TimeInterval) -> LlmJobResult? {
    gate.lock(); defer { gate.unlock() }
    guard timeout.isFinite, timeout >= 0, workerThread !== Thread.current else { return nil }
    let deadline = Date(timeIntervalSinceNow: timeout)
    while result == nil { if !gate.wait(until: deadline) { return result } }
    return result
  }
  private var stopped: Bool { gate.lock(); defer { gate.unlock() }; return cancelled }
  private func current(_ ticket: LlmWorkTicket) -> Bool { !stopped && controller.llmWorkAllowed(ticket) }
  private func finish(_ ticket: LlmWorkTicket, _ outcome: LlmJobResult, lease: LlmPackLease? = nil) {
    request?.cancel();prompt.cancel()
    gate.lock(); let old = stream; stream = nil; gate.unlock(); old?.close()
    let accepted = controller.finishLlmWork(ticket, result: stopped || ticket.cancelled || ticket.token.cancelled ? .cancelled : outcome,
      verified: { lease?.verified() == true && !self.stopped })
    lease?.close()
    gate.lock(); result = accepted; gate.broadcast(); gate.unlock();completion(accepted)
  }
  private func run(_ ticket: LlmWorkTicket, store: PackStore, selection: LlmPackSelection,
                   threads: Int, limit: Int, api: NativeLlmAPI, request:GenericReplyRequest?,
                   open: (URL, LlmArtifactPin) throws -> LlmVerifiedDescriptor,
                   consume: (UnsafeBufferPointer<UInt8>) throws -> Void) {
    gate.lock(); workerThread = Thread.current; gate.unlock()
    var lease: LlmPackLease?, outcome = LlmJobResult.unavailable
    defer { finish(ticket, outcome, lease: lease) }
    do {
      guard current(ticket) else { outcome = .cancelled; return }
      let verified = try LlmPackLease.resolve(store: store, selection: selection); lease = verified
      let loaded = try verified.openStream(allowed: { self.current(ticket) }, threads: threads, api: api,
        openDescriptor: open, created: { candidate in
          self.gate.lock(); self.stream = candidate; self.gate.unlock()
          if !self.current(ticket) { candidate.requestCancellation() }
        })
      if let request {
        let plan=try PromptBudget.build(latest:request.latest,history:request.history,outputLimit:limit,count:loaded.countTokens)
        var bytes=Array(plan.text.utf8);defer{bytes.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
        let planned=try bytes.withUnsafeBufferPointer{try LlmOwnedPrompt($0)};defer{planned.cancel()}
        guard planned.claim(),current(ticket) else{throw LlmFailure.cancelled}
        prompt.cancel();try planned.withBorrow{try loaded.begin($0,outputLimit:limit)}
      }else{try prompt.withBorrow { try loaded.begin($0, outputLimit: limit) }}
      var pieces = 0, rejected = false
      while try loaded.withNextPiece({ bytes in
        guard pieces < limit else { rejected = true; return }
        if !self.controller.consumeLlmPiece(ticket, verified: { verified.verified() && !self.stopped }, bytes: bytes, consume: consume) { rejected = true }
        pieces += 1
      }) {
        if rejected { throw LlmFailure.unavailable }
      }
      outcome = !current(ticket) ? .cancelled : (verified.verified() ? .completed : .unavailable)
    } catch { outcome = stopped || ticket.cancelled || ticket.token.cancelled ? .cancelled : .unavailable }
  }
  /// Internal descriptor/thread/scheduler seams are only for synthetic native tests.
  static func submit(controller: NativeController, token: GenerationToken, store: PackStore,
                     selection: LlmPackSelection, prompt: LlmOwnedPrompt, outputLimit: Int = 256,
                     threads: Int = 2, api: NativeLlmAPI = .linked,
                     open: @escaping (URL, LlmArtifactPin) throws -> LlmVerifiedDescriptor = LlmModelDescriptor.open,
                     schedule: (@escaping () -> Void) throws -> Void = { work in worker.async(execute: DispatchWorkItem(block: work)) },
                     workerAllowed: @escaping () -> Bool = { !Thread.isMainThread },
                     request:GenericReplyRequest?=nil,completion:@escaping(LlmJobResult)->Void={_ in},
                     consume: @escaping (UnsafeBufferPointer<UInt8>) throws -> Void) -> LlmControllerJob? {
    guard prompt.claim() else { return nil } // Never erase an already transferred live prompt.
    guard (1...256).contains(outputLimit), (1...8).contains(threads) else { prompt.cancel();request?.cancel(); return nil }
    let job = LlmControllerJob(controller: controller, prompt: prompt,completion:completion,request:request)
    guard let ticket = controller.prepareLlmWork(token, cancel: { [weak job] in job?.requestCancellation() }) else { prompt.cancel();request?.cancel(); return nil }
    let caller = Thread.current
    do { try schedule {
      guard Thread.current !== caller, workerAllowed() else { job.finish(ticket, .unavailable); return }
      job.run(ticket, store: store, selection: selection, threads: threads, limit: outputLimit, api: api, request:request, open: open, consume: consume)
    } } catch { job.finish(ticket, .unavailable) }
    return job
  }
}
