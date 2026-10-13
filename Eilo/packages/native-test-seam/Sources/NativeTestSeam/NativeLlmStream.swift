import Foundation
#if canImport(CEiloLlm)
import CEiloLlm
#endif

enum LlmFailure: Error { case unavailable, cancelled }

/// Injectable native boundary for lifecycle tests; no prompt or token crosses JS.
struct NativeLlmAPI {
  let create: () -> OpaquePointer?
  let load: (OpaquePointer, Int32, Int32) -> Int32
  let begin: (OpaquePointer, UnsafeBufferPointer<UInt8>, Int32) -> Int32
  let next: (OpaquePointer, UnsafeMutableBufferPointer<CChar>, inout Int32) -> Int32
  let cancel: (OpaquePointer) -> Void
  let destroy: (OpaquePointer) -> Void

  let countTokens:(OpaquePointer,UnsafeBufferPointer<UInt8>)->Int32
  init(create:@escaping()->OpaquePointer?,load:@escaping(OpaquePointer,Int32,Int32)->Int32,
       begin:@escaping(OpaquePointer,UnsafeBufferPointer<UInt8>,Int32)->Int32,
       next:@escaping(OpaquePointer,UnsafeMutableBufferPointer<CChar>,inout Int32)->Int32,
       cancel:@escaping(OpaquePointer)->Void,destroy:@escaping(OpaquePointer)->Void,
       countTokens:@escaping(OpaquePointer,UnsafeBufferPointer<UInt8>)->Int32={_,_ in -3}){
    self.create=create;self.load=load;self.begin=begin;self.next=next;self.cancel=cancel;self.destroy=destroy;self.countTokens=countTokens
  }
  static var linked: NativeLlmAPI {
    #if canImport(CEiloLlm) && DEBUG && EILO_LLM_EVALUATION
    return NativeLlmAPI(create: { eilo_llm_create() },
      load: { eilo_llm_load($0, $1, $2) },
      begin: { handle, prompt, limit in
        prompt.withMemoryRebound(to: CChar.self) {
          eilo_llm_begin(handle, $0.baseAddress, Int32($0.count), limit)
        }
      }, next: { eilo_llm_next($0, $1.baseAddress, Int32($1.count), &$2) },
      cancel: { eilo_llm_cancel($0) }, destroy: { eilo_llm_destroy($0) }, countTokens:{handle,bytes in
        bytes.withMemoryRebound(to:CChar.self){eilo_llm_count_tokens(handle,$0.baseAddress,Int32($0.count))}
      })
    #else
    return NativeLlmAPI(create: { nil }, load: { _, _, _ in -3 },
      begin: { _, _, _ in -3 }, next: { _, _, bytes in bytes = 0; return -3 },
      cancel: { _ in }, destroy: { _ in })
    #endif
  }
}

/// All operations and destruction belong to one serialized native worker, except
/// requestCancellation. Join that worker before releasing the last reference.
/// The caller supplies a current controller/privacy/verified-model lease, hashes
/// the immutable exclusively borrowed FD, and retains it until load returns.
final class NativeLlmStream {
  private enum Phase { case created, loaded, generating, closed }
  private let lifetime = NSLock()
  private let api: NativeLlmAPI
  private let allowed: () -> Bool
  private var handle: OpaquePointer?
  private var cancelled = false
  private var phase = Phase.created
  private var scratch = [CChar](repeating: 0, count: 1024)

  init(allowed: @escaping () -> Bool, api: NativeLlmAPI = .linked) throws {
    self.allowed = allowed; self.api = api
    guard allowed(), let candidate = api.create() else { throw LlmFailure.unavailable }
    guard allowed() else { api.destroy(candidate); throw LlmFailure.unavailable }
    handle = candidate
  }

  func load(verifiedDescriptor: Int32, threads: Int = 2) throws {
    let current = try checkedHandle()
    guard phase == .created, verifiedDescriptor >= 0, (1...8).contains(threads) else {
      try fail()
    }
    try accept(api.load(current, verifiedDescriptor, Int32(threads)))
    phase = .loaded
  }

  /// Worker-only loaded vocabulary with the same special-token flags as begin.
  func countTokens(_ text:String)throws->Int {
    var bytes=Array(text.utf8);defer{bytes.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
    let current=try checkedHandle()
    guard phase == .loaded,(1...16384).contains(bytes.count),!bytes.contains(0) else{try fail()}
    let result=bytes.withUnsafeBufferPointer{api.countTokens(current,$0)};_ = try checkedHandle()
    guard (1...32768).contains(result) else{try fail(result)};return Int(result)
  }

  /// Borrows preformatted bytes only for this call. Template/speech policy is separate.
  func begin(_ prompt: UnsafeBufferPointer<UInt8>, outputLimit: Int) throws {
    let current = try checkedHandle()
    guard phase == .loaded, (1...16384).contains(prompt.count),
      !prompt.contains(0), (1...256).contains(outputLimit) else { try fail() }
    try accept(api.begin(current, prompt, Int32(outputLimit)))
    phase = .generating
  }

  /// Returns true for one raw piece, false at completion. The borrowed piece may
  /// split UTF-8 and is valid only within consume. No String/retained copy is made.
  /// Consumer must revalidate before eventual display/speech/storage; this callback
  /// grants no speech authorization and cannot make a later Stop race impossible.
  func withNextPiece(_ consume: (UnsafeBufferPointer<UInt8>) -> Void) throws -> Bool {
    defer { clearScratch() }
    let current = try checkedHandle()
    guard phase == .generating else { try fail() }
    var bytes: Int32 = 0
    let result = scratch.withUnsafeMutableBufferPointer { api.next(current, $0, &bytes) }
    _ = try checkedHandle()
    if result == 0 && bytes == 0 { close(); return false }
    guard result == 1, (1...1024).contains(bytes) else { try fail(result) }
    scratch.withUnsafeBufferPointer { buffer in
      buffer.withMemoryRebound(to: UInt8.self) {
        consume(UnsafeBufferPointer(rebasing: $0[..<Int(bytes)]))
      }
    }
    return true
  }

  /// Never waits for decode or destroys the handle. The short lifetime lock only
  /// prevents cancellation from touching a pointer already detached for destruction.
  func requestCancellation() {
    lifetime.lock(); defer { lifetime.unlock() }
    cancelled = true
    if let handle { api.cancel(handle) }
  }

  func close() {
    lifetime.lock()
    cancelled = true
    let old = handle; handle = nil
    if let old { api.cancel(old) }
    lifetime.unlock()
    phase = .closed; clearScratch()
    if let old { api.destroy(old) }
  }

  private func checkedHandle() throws -> OpaquePointer {
    lifetime.lock()
    let current = handle, stopped = cancelled
    lifetime.unlock()
    guard let current, !stopped, allowed() else { try fail(stopped ? -2 : -3) }
    return current
  }

  private func accept(_ result: Int32) throws {
    _ = try checkedHandle()
    guard result == 0 else { try fail(result) }
  }

  private func fail(_ result: Int32 = -3) throws -> Never {
    close()
    throw result == -2 ? LlmFailure.cancelled : LlmFailure.unavailable
  }

  private func clearScratch() {
    scratch.withUnsafeMutableBufferPointer { $0.initialize(repeating: 0) }
  }
  deinit { close() }
}
