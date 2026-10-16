import Foundation

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
  func close(){lock.lock();defer{lock.unlock()};bytes.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)};live=false}
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
  init(available:@escaping ()->Bool={false}){self.available=available}
  private var query:[String:Any]{[kSecClass as String:kSecClassGenericPassword,
    kSecAttrService as String:"com.eilo.protected-memory.v1",kSecAttrAccount as String:"database-key",
    kSecAttrSynchronizable as String:false]}
  func create()throws {
    guard available(),let access=SecAccessControlCreateWithFlags(nil,kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,.userPresence,nil) else{throw ProtectedKeyFailure.unavailable}
    var bytes=[UInt8](repeating:0,count:32);defer{bytes.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
    guard SecRandomCopyBytes(kSecRandomDefault,bytes.count,&bytes)==errSecSuccess else{throw ProtectedKeyFailure.unavailable}
    var data=Data(bytes);defer{data.resetBytes(in:0..<data.count)}
    var q=query;q[kSecAttrAccessControl as String]=access;q[kSecValueData as String]=data
    guard available(),SecItemAdd(q as CFDictionary,nil)==errSecSuccess else{throw ProtectedKeyFailure.unavailable}
  }
  func load()throws->ProtectedKey {
    guard available() else{throw ProtectedKeyFailure.unavailable}
    let context=LAContext();context.touchIDAuthenticationAllowableReuseDuration=0
    defer{context.invalidate()}
    var q=query;q[kSecReturnData as String]=true;q[kSecMatchLimit as String]=kSecMatchLimitOne
    q[kSecUseAuthenticationContext as String]=context
    q[kSecUseOperationPrompt as String]="Authenticate to access local Eilo memory"
    var result:CFTypeRef?
    guard SecItemCopyMatching(q as CFDictionary,&result)==errSecSuccess,var data=result as? Data else{throw ProtectedKeyFailure.unavailable}
    defer{data.resetBytes(in:0..<data.count)}
    guard available(),data.count==32 else{throw ProtectedKeyFailure.unavailable}
    return try ProtectedKey(Array(data))
  }
}
#endif
