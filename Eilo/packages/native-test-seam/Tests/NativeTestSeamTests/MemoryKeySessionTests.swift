import XCTest
@testable import NativeTestSeam
final class MemoryKeySessionTests:XCTestCase {
  final class Clock:NativeClock{var now:UInt64=100;func milliseconds()->UInt64{now}}
  final class Timer:IdleScheduler,IdleCancellation{var tasks=[()->Void]();func cancel(){};func schedule(_ ms:UInt64,task:@escaping ()->Void)->any IdleCancellation{tasks.append(task);return self}}
  func key()throws->ProtectedKey{try ProtectedKey([UInt8](repeating:9,count:32))}
  func testExplicitAuthenticationExpiryAndLateResult()throws {
    let clock=Clock(),timer=Timer();var unlocked=true
    let s=MemoryKeySession(clock:clock,scheduler:timer,unlocked:{unlocked})
    XCTAssertFalse(s.allows(.readMemory));let t=s.beginAuthentication()!,k=try key()
    XCTAssertTrue(s.complete(t,key:k));XCTAssertTrue(s.allows(.readMemory))
    clock.now+=60_000;XCTAssertFalse(s.allows(.commitHistory));XCTAssertFalse(k.active)
    let old=s.beginAuthentication()!;s.revoke();let late=try key();XCTAssertFalse(s.complete(old,key:late));XCTAssertFalse(late.active)
    unlocked=false;XCTAssertNil(s.beginAuthentication());unlocked=true;XCTAssertFalse(s.allows(.readMemory))
  }
  func testOldTimerAndDuplicateCompletionCannotReplaceNewSession()throws {
    let timer=Timer(),s=MemoryKeySession(scheduler:timer,unlocked:{true})
    let a=s.beginAuthentication()!,ka=try key();XCTAssertTrue(s.complete(a,key:ka))
    let b=s.beginAuthentication()!,kb=try key();XCTAssertTrue(s.complete(b,key:kb));timer.tasks[0]()
    XCTAssertTrue(s.allows(.readMemory));XCTAssertFalse(ka.active)
    let duplicate=try key();XCTAssertFalse(s.complete(b,key:duplicate));XCTAssertFalse(duplicate.active);XCTAssertTrue(kb.active)
    timer.tasks[1]();XCTAssertFalse(kb.active)
  }
  func testRevokeDestroysAllOwnedCopiesAndRejectsDeniedAuthenticationReuse()throws {
    let s=MemoryKeySession(unlocked:{true}),k=try key(),t=s.beginAuthentication()!
    XCTAssertTrue(s.complete(t,key:k));let copies=try (0..<8).map{_ in try s.copyForNativeUse()}
    XCTAssertThrowsError(try s.copyForNativeUse());s.revoke()
    XCTAssertFalse(k.active);for copy in copies{XCTAssertFalse(copy.active);XCTAssertThrowsError(try copy.borrow{_ in XCTFail("revoked copy")})}
    XCTAssertThrowsError(try s.copyForNativeUse())
    let clock=Clock(),a=MemoryKeySession(clock:clock,unlocked:{true}),ticket=a.beginAuthentication()!
    clock.now+=30_000;XCTAssertFalse(a.complete(ticket,key:try key()));clock.now=100
    XCTAssertFalse(a.complete(ticket,key:try key()))
  }

}
