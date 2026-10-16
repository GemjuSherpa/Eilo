import Foundation
import Darwin

/// Darwin explicit erasure is not removable as a dead store. This only covers owned storage.
private func eraseKeyBytes(_ bytes:inout [UInt8]) {
  bytes.withUnsafeMutableBytes{buffer in
    if let base=buffer.baseAddress {_ = memset_s(base,buffer.count,0,buffer.count)}
  }
}

/// Native owned key storage. Borrow synchronously; no JS, logging or persistence sink.
/// Erasure covers this allocation, not OS/vendor copies or a hostile native borrower.
final class ProtectedKey {
  private let lock=NSRecursiveLock()
  private var bytes:[UInt8]
  private var live=true
  init(_ input:[UInt8])throws {guard input.count==32 else{throw ProtectedKeyFailure.unavailable};bytes=input}
  func borrow(_ body:(UnsafeBufferPointer<UInt8>)throws->Void)throws {
    lock.lock();defer{lock.unlock()};guard live else{throw ProtectedKeyFailure.unavailable}
    try bytes.withUnsafeBufferPointer(body)
  }
  func close(){lock.lock();defer{lock.unlock()};eraseKeyBytes(&bytes);live=false}
  var active:Bool{lock.lock();defer{lock.unlock()};return live}
  deinit{close()}
}
enum ProtectedKeyFailure:Error {case unavailable}

#if os(iOS)
import Security
import LocalAuthentication
/// Explicit worker-only OS operations; never called at startup. A missing item is not regenerated
/// during reads, so invalidation cannot silently replace a key protecting existing ciphertext.
final class IOSProtectedKeyProvider {
  private let available:()->Bool
  private let requestLock=NSLock()
  private var current:LAContext?
  func cancel(){requestLock.lock();let old=current;current=nil;requestLock.unlock();old?.invalidate()}
  init(available:@escaping ()->Bool={false}){self.available=available}
  private var query:[String:Any]{[kSecClass as String:kSecClassGenericPassword,
    kSecAttrService as String:"com.eilo.protected-memory.v1",kSecAttrAccount as String:"database-key",
    kSecAttrSynchronizable as String:false]}
  func create()throws {
    guard available(),let access=SecAccessControlCreateWithFlags(nil,kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,.userPresence,nil) else{throw ProtectedKeyFailure.unavailable}
    var bytes=[UInt8](repeating:0,count:32);defer{eraseKeyBytes(&bytes)}
    guard SecRandomCopyBytes(kSecRandomDefault,bytes.count,&bytes)==errSecSuccess else{throw ProtectedKeyFailure.unavailable}
    var data=Data(bytes);defer{data.withUnsafeMutableBytes{buffer in if let base=buffer.baseAddress{_ = memset_s(base,buffer.count,0,buffer.count)}}}
    var q=query;q[kSecAttrAccessControl as String]=access;q[kSecValueData as String]=data
    guard available(),SecItemAdd(q as CFDictionary,nil)==errSecSuccess else{throw ProtectedKeyFailure.unavailable}
  }
  func load()throws->ProtectedKey {
    guard available() else{throw ProtectedKeyFailure.unavailable}
    let context=LAContext();context.touchIDAuthenticationAllowableReuseDuration=0
    requestLock.lock();guard current==nil else{requestLock.unlock();throw ProtectedKeyFailure.unavailable};current=context;requestLock.unlock()
    defer{requestLock.lock();if current === context{current=nil};requestLock.unlock();context.invalidate()}
    var q=query;q[kSecReturnData as String]=true;q[kSecMatchLimit as String]=kSecMatchLimitOne
    q[kSecUseAuthenticationContext as String]=context
    q[kSecUseOperationPrompt as String]="Authenticate to access local Eilo memory"
    var result:CFTypeRef?
    guard SecItemCopyMatching(q as CFDictionary,&result)==errSecSuccess,var data=result as? Data else{throw ProtectedKeyFailure.unavailable}
    defer{data.withUnsafeMutableBytes{buffer in if let base=buffer.baseAddress{_ = memset_s(base,buffer.count,0,buffer.count)}}}
    requestLock.lock();let valid=current === context;requestLock.unlock()
    guard valid,available(),data.count==32 else{throw ProtectedKeyFailure.unavailable}
    return try ProtectedKey(Array(data))
  }
}
#endif

/// Native authentication result consumes one pre-auth ticket. Unlock alone cannot authorize.
/// No production caller or protected store is installed; S08 still gates persistent memory.
enum PrivilegedOrigin:CaseIterable {case authenticatedScreen,wake,voice,model}
enum PrivilegedOperation:CaseIterable {case readMemory,deleteHistory,changePrivacy}
final class MemoryKeySession:PrivateEffectGate {
  struct Ticket {fileprivate let epoch:UUID,started:UInt64}
  private let lock=NSRecursiveLock(),clock:any NativeClock,scheduler:any IdleScheduler,unlocked:()->Bool
  private var epoch=UUID(),pending=false,key:ProtectedKey?,opened:UInt64=0
  private var copies=[ProtectedKey]()
  private var expiry:(any IdleCancellation)?
  init(clock:any NativeClock=MonotonicClock(),scheduler:any IdleScheduler=NativeIdleScheduler(),unlocked:@escaping ()->Bool={false}) {
    self.clock=clock;self.scheduler=scheduler;self.unlocked=unlocked
  }
  func beginAuthentication()->Ticket? {
    lock.lock();defer{lock.unlock()};revoke()
    guard unlocked() else{return nil};pending=true
    return Ticket(epoch:epoch,started:clock.milliseconds())
  }
  /// Called only after the native provider obtained the key under OS authentication.
  @discardableResult func complete(_ ticket:Ticket,key candidate:ProtectedKey)->Bool {
    lock.lock();defer{lock.unlock()}
    let now=clock.milliseconds()
    guard pending,ticket.epoch==epoch,unlocked(),candidate.active,now>=ticket.started,now-ticket.started<30_000,pending,ticket.epoch==epoch else{candidate.close();if ticket.epoch==epoch && pending{revoke()};return false}
    pending=false;key=candidate;opened=now;let accepted=epoch
    expiry=scheduler.schedule(60_000){[weak self] in self?.expire(accepted)}
    return true
  }
  private func expire(_ expected:UUID){lock.lock();defer{lock.unlock()};if epoch==expected{revoke()}}
  func allows(_ effect:PrivateEffect)->Bool {
    lock.lock();defer{lock.unlock()};let now=clock.milliseconds()
    guard unlocked() else{revoke();return false}
    guard let key else{return false} // A denied read must not cancel an in-flight authentication.
    guard key.active,now>=opened,now-opened<60_000 else{revoke();return false}
    return true
  }
  /// Every owned native copy remains registered until session revocation.
  func copyForNativeUse()throws->ProtectedKey {
    lock.lock();defer{lock.unlock()}
    guard allows(.readMemory),copies.count<8,let key else{throw ProtectedKeyFailure.unavailable}
    var bytes=[UInt8]();defer{eraseKeyBytes(&bytes)}
    try key.borrow{bytes=Array($0)};let copy=try ProtectedKey(bytes);copies.append(copy);return copy
  }
  func revoke(){lock.lock();defer{lock.unlock()};epoch=UUID();pending=false;expiry?.cancel();expiry=nil;copies.forEach{$0.close()};copies.removeAll();key?.close();key=nil}
  /// Native origin is chosen by the trusted dispatcher, never parsed from model/text payloads.
  func allowsPrivilegedRequest(origin:PrivilegedOrigin,operation:PrivilegedOperation)->Bool {
    lock.lock();defer{lock.unlock()}
    switch operation {case .readMemory,.deleteHistory,.changePrivacy:return origin == .authenticatedScreen && allows(.readMemory)}
  }
  func invalidate(){revoke()}
  deinit{revoke()}
}
