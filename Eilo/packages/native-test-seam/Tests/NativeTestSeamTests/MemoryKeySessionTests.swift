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

  func testLockRevokesBeforeCancellationAndWithholdsPrivateEffectsInEveryVoicePhase()throws {
    for phase in 0..<3 {
      let session=MemoryKeySession(unlocked:{true}),e=EffectsSpy(),c=testController(effects:e,privateGate:session)
      _ = c.privacyTransition(.historySession);XCTAssertTrue(c.dispatch(.start));XCTAssertTrue(c.dispatch(.speechDetected,token:c.token))
      if phase>0{XCTAssertTrue(c.dispatch(.endpoint,token:c.token))};if phase>1{XCTAssertTrue(c.dispatch(.speechReady,token:c.token))}
      let token=c.token!,ticket=session.beginAuthentication()!,k=try key()
      XCTAssertTrue(session.complete(ticket,key:k));let copy=try session.copyForNativeUse()
      e.onCancel={XCTAssertFalse(k.active);XCTAssertFalse(copy.active)}
      _ = c.privacyTransition(.lock);XCTAssertEqual(c.state,.stopped);XCTAssertTrue(e.context.isEmpty)
      XCTAssertFalse(c.guardedPrivateEffect(token,effect:.displayPrivate){XCTFail("stale private sink")})
    }
  }

  func testWakeVoiceModelCannotAcquirePrivilegesEvenDuringAuthenticatedSession()throws {
    var unlocked=true;let s=MemoryKeySession(unlocked:{unlocked})
    XCTAssertTrue(s.complete(s.beginAuthentication()!,key:try key()))
    for op in PrivilegedOperation.allCases {
      for origin in [PrivilegedOrigin.wake,.voice,.model]{XCTAssertFalse(s.allowsPrivilegedRequest(origin:origin,operation:op))}
      XCTAssertTrue(s.allowsPrivilegedRequest(origin:.authenticatedScreen,operation:op))
    }
    unlocked=false
    for origin in PrivilegedOrigin.allCases{for op in PrivilegedOperation.allCases{XCTAssertFalse(s.allowsPrivilegedRequest(origin:origin,operation:op))}}
    unlocked=true;XCTAssertFalse(s.allowsPrivilegedRequest(origin:.authenticatedScreen,operation:.deleteHistory))
  }

  func testUnlockNeedsFreshAuthenticationAndOldResultCannotReviveSession()throws {
    let session=MemoryKeySession(unlocked:{true}),c=testController(privateGate:session)
    _ = c.privacyTransition(.historySession);_ = c.dispatch(.start)
    let old=session.beginAuthentication()!;_ = c.privacyTransition(.lock);_ = c.privacyTransition(.unlock)
    XCTAssertTrue(c.dispatch(.start));let token=c.token!
    XCTAssertFalse(c.guardedPrivateEffect(token,effect:.readMemory){XCTFail("unlock granted memory")})
    let late=try key();XCTAssertFalse(session.complete(old,key:late));XCTAssertFalse(late.active)
    XCTAssertTrue(session.complete(session.beginAuthentication()!,key:try key()))
    var reads=0;XCTAssertTrue(c.guardedPrivateEffect(token,effect:.readMemory){reads+=1});XCTAssertEqual(reads,1)
    _ = c.stop();XCTAssertFalse(session.allows(.readMemory))
  }
  func testStopAndClockRollbackInvalidateCopiesAndPendingAuthentication()throws {
    let clock=Clock(),session=MemoryKeySession(clock:clock,unlocked:{true}),c=testController(privateGate:session)
    _ = c.dispatch(.start);let k=try key();XCTAssertTrue(session.complete(session.beginAuthentication()!,key:k))
    let copy=try session.copyForNativeUse();_ = c.stop();XCTAssertFalse(k.active);XCTAssertFalse(copy.active)
    let t=session.beginAuthentication()!;_ = c.stop();XCTAssertFalse(session.complete(t,key:try key()))
    XCTAssertTrue(session.complete(session.beginAuthentication()!,key:try key()));clock.now=99
    XCTAssertFalse(session.allows(.readMemory));clock.now=100;XCTAssertFalse(session.allows(.readMemory))
  }

  func testPrivateEffectCannotReportCurrentAuthorizationAfterExpiry()throws {
    let clock=Clock(),session=MemoryKeySession(clock:clock,unlocked:{true}),c=testController(privateGate:session)
    _ = c.privacyTransition(.historySession);_ = c.dispatch(.start)
    XCTAssertTrue(session.complete(session.beginAuthentication()!,key:try key()))
    XCTAssertFalse(c.guardedPrivateEffect(c.token!,effect:.displayPrivate){clock.now+=60_000})
    XCTAssertFalse(session.allows(.readMemory))
  }

}
