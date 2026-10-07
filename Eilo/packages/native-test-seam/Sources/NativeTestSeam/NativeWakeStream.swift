import Foundation
#if canImport(CEiloWake)
import CEiloWake
#endif

/// Paths come from a separately verified native model pack, never the JS bridge.
struct WakeModelPaths {
  let encoder:String, decoder:String, joiner:String, tokens:String
  init(encoder:String,decoder:String,joiner:String,tokens:String) throws {
    guard [encoder,decoder,joiner,tokens].allSatisfy({
      $0.hasPrefix("/") && !$0.utf8.contains(0) && $0.utf8.count <= 4096
    }) else { throw WakeFailure.unavailable }
    self.encoder=encoder;self.decoder=decoder;self.joiner=joiner;self.tokens=tokens
  }
}

/// Injectable only for lifetime/error tests. The linked implementation calls the real C ABI.
struct NativeWakeAPI {
  let create:(WakeModelPaths,WakeConfiguration)->OpaquePointer?
  let process:(OpaquePointer,UnsafeBufferPointer<Float>,Int)->Int32
  let destroy:(OpaquePointer)->Void
  static var linked:NativeWakeAPI {
    #if canImport(CEiloWake) && DEBUG && EILO_WAKE_EVALUATION
    return NativeWakeAPI(create:{ paths,config in
      paths.encoder.withCString { encoder in paths.decoder.withCString { decoder in
        paths.joiner.withCString { joiner in paths.tokens.withCString { tokens in
          eilo_wake_create(encoder,decoder,joiner,tokens,config.threshold,config.boost)
        } }
      } }
    },process:{ handle,samples,rate in
      eilo_wake_process(handle,samples.baseAddress,Int32(samples.count),Int32(rate))
    },destroy:{ eilo_wake_destroy($0) })
    #else
    return NativeWakeAPI(create:{ _,_ in nil },process:{ _,_,_ in -1 },destroy:{ _ in })
    #endif
  }
}

/// Serialized native worker binding. C++ owns decode/reset; Swift exposes only its fixed wake label.
/// No feature availability or manifest trust is granted by linking a library.
final class NativeWakeStream:WakeKeywordStream {
  private let lock=NSRecursiveLock()
  private let api:NativeWakeAPI
  private let verified:()->Bool
  private var handle:OpaquePointer?
  private var matched=false
  private var sampleRate:Int?
  init(paths:WakeModelPaths,configuration:WakeConfiguration,verified:@escaping ()->Bool,
       api:NativeWakeAPI = .linked) throws {
    self.api=api;self.verified=verified
    // The C runtime has exactly one keyword; reject configurations that imply another phrase.
    guard configuration.phrase=="HEY EILO",verified(),let candidate=api.create(paths,configuration) else {
      throw WakeFailure.unavailable
    }
    guard verified() else { api.destroy(candidate);throw WakeFailure.unavailable }
    handle=candidate
  }
  func accept(_ samples:UnsafeBufferPointer<Float>,sampleRate:Int) throws {
    lock.lock();defer { lock.unlock() }
    guard let current=handle,verified(),(8000...192000).contains(sampleRate),
      !samples.isEmpty,samples.count <= sampleRate/10,
      samples.allSatisfy({ $0.isFinite && (-1...1).contains($0) }),
      self.sampleRate == nil || self.sampleRate == sampleRate else {
      close();throw WakeFailure.unavailable
    }
    self.sampleRate=sampleRate
    let result=api.process(current,samples,sampleRate)
    guard result==0 || result==1,verified() else { close();throw WakeFailure.unavailable }
    matched=matched || result==1
  }
  func ready() throws -> Bool { lock.lock();defer { lock.unlock() };try check();return false }
  func decode() throws { throw WakeFailure.unavailable } // C++ already decodes within accept.
  func keyword() throws -> String { lock.lock();defer { lock.unlock() };try check();return matched ? "HEY EILO" : "" }
  func reset() throws { lock.lock();defer { lock.unlock() };try check();matched=false }
  private func check() throws {
    guard handle != nil,verified() else { close();throw WakeFailure.unavailable }
  }
  func close() {
    lock.lock();defer { lock.unlock() }
    let previous=handle;handle=nil;matched=false;sampleRate=nil
    if let previous { api.destroy(previous) }
  }
  deinit { close() }
}
