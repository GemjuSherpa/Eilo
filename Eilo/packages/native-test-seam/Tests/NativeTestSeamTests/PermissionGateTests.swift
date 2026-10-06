import XCTest
@testable import NativeTestSeam
final class FakePermission: MicrophonePermissionAdapter {
  var value: MicrophonePermission
  var requests=0
  var callback: ((MicrophonePermission) -> Void)?
  init(_ value: MicrophonePermission = .granted) { self.value=value }
  func status() -> MicrophonePermission { value }
  func request(_ completion: @escaping (MicrophonePermission) -> Void) { requests += 1; callback=completion }
  func complete(_ result: MicrophonePermission) { value=result; callback?(result) }
}
struct ReadyModels: ModelReadinessAdapter { func status() -> ModelStatus { .ready } }
func testController(diagnostics: SafeDiagnostics=SafeDiagnostics(),effects: any ControllerEffects=EffectsSpy(),privateGate: any PrivateEffectGate=DeniedPrivateEffectGate(),clock: any NativeClock=FakeTime(),scheduler: any IdleScheduler=FakeTime(),permission: any MicrophonePermissionAdapter=FakePermission()) -> NativeController { NativeController(diagnostics:diagnostics,effects:effects,privateGate:privateGate,clock:clock,scheduler:scheduler,permission:permission,models:ReadyModels()) }
final class PermissionGateTests: XCTestCase {
  func testMatrixExplicitStartAndNoDenialLoop() {
    for status in MicrophonePermission.allCases {
      let p=FakePermission(status), spy=EffectsSpy(); let c=testController(effects:spy,permission:p)
      XCTAssertEqual(p.requests,0); XCTAssertEqual(spy.started,0)
      c.dispatch(.start); XCTAssertEqual(spy.started,status == .granted ? 1 : 0)
      if status == .notRequested { XCTAssertEqual(p.requests,1); p.complete(.denied); for _ in 0..<3 { c.dispatch(.start) }; XCTAssertEqual(p.requests,1); XCTAssertEqual(spy.started,0) }
    }
  }
  func testLateGrantAndDuplicateCallbackNeverCapture() {
    let p=FakePermission(.notRequested), spy=EffectsSpy(); let c=testController(effects:spy,permission:p)
    c.dispatch(.start); c.stop(); p.complete(.granted); XCTAssertEqual(spy.started,0); XCTAssertEqual(c.state,.stopped)
    c.dispatch(.start); p.complete(.granted); XCTAssertEqual(spy.started,1)
  }
  func testRevocationRejectsOutputAndReleasesCapture() {
    let p=FakePermission(), spy=EffectsSpy(); let c=testController(effects:spy,permission:p)
    c.dispatch(.start); c.dispatch(.speechDetected,token:c.token); c.dispatch(.endpoint,token:c.token); let old=c.token!
    p.value = .denied; XCTAssertFalse(c.releaseSpeech(old,clause:"revoked")); XCTAssertEqual(spy.released,1); XCTAssertTrue(spy.clauses.isEmpty); XCTAssertEqual(c.state,.stopped)
  }
  func testPendingRepeatedStartAndReentrantStop() {
    let p=FakePermission(.notRequested), spy=EffectsSpy(); let c=testController(effects:spy,permission:p)
    c.dispatch(.start); XCTAssertFalse(c.dispatch(.start)); p.complete(.granted); XCTAssertEqual(spy.started,1)
    c.stop(); spy.onStart={ c.stop() }; XCTAssertFalse(c.dispatch(.start)); XCTAssertEqual(c.state,.stopped); XCTAssertNil(c.token)
  }
  func testMissingProductionAdapterFailsClosed() {
    let spy=EffectsSpy(); let c=NativeController(effects:spy)
    XCTAssertFalse(c.dispatch(.start)); XCTAssertEqual(spy.started,0)
  }
}
