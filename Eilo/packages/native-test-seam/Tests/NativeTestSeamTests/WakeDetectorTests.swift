import XCTest
@testable import NativeTestSeam
private final class KeywordFixture: WakeKeywordStream {
  var expectedRate=16000
  var onAccept:(()->Void)?
  var onDecode:((Int)->Void)?
  var result="",fail="";var pending=2,accepted=0,decoded=0,resets=0,closed=0;var endless=false
  var borrowed:UnsafeBufferPointer<Float>?
  func accept(_ samples:UnsafeBufferPointer<Float>,sampleRate:Int) throws {
    accepted += 1;borrowed=samples;onAccept?();XCTAssertEqual(sampleRate,expectedRate);XCTAssertEqual(Array(samples),[-1,-0.5,0,0.5])
    if fail=="accept" { throw WakeFailure.unavailable }
  }
  func ready() throws -> Bool { if fail=="ready" { throw WakeFailure.unavailable };return endless || pending>0 }
  func decode() throws { decoded += 1;pending -= 1;onDecode?(decoded);if fail=="decode" { throw WakeFailure.unavailable } }
  func keyword() throws -> String { if fail=="result" { throw WakeFailure.unavailable };return result }
  func reset() throws { resets += 1;result="";if fail=="reset" { throw WakeFailure.unavailable } }
  func close() throws { closed += 1;if fail=="close" { throw WakeFailure.unavailable } }
}
final class WakeDetectorTests: XCTestCase {
  private var config:WakeConfiguration { try! WakeConfiguration(phrase:"HEY EILO",threshold:0.6,boost:1.5) }
  private let pcm:[Float]=[-1,-0.5,0,0.5]
  private func process(_ d:WakeDetector,_ t:GenerationToken)->WakeActivation? { pcm.withUnsafeBufferPointer { d.process(t,input:$0,sampleRate:16000) } }
  func testFrozenKeywordResultsGateActivationWithoutConversationalWork() {
    let effects=EffectsSpy();let c=testController(effects:effects);c.dispatch(.start);let t=c.token!,engine=KeywordFixture()
    let d=WakeDetector(configuration:config,verified:{true},open:{ configuration in XCTAssertEqual(configuration.phrase,"HEY EILO");XCTAssertEqual(configuration.threshold,0.6);return engine });XCTAssertTrue(d.begin(t))
    for result in ["","ordinary speech","HEY OTHER","HEY EILO trailing"] { engine.result=result;XCTAssertNil(process(d,t));XCTAssertEqual(c.state,.standby);XCTAssertTrue(engine.borrowed!.allSatisfy {$0==0}) }
    engine.result="HEY EILO";let event=process(d,t)!;XCTAssertEqual(c.state,.standby);XCTAssertTrue(event.apply(c));XCTAssertEqual(c.state,.capturing);XCTAssertFalse(event.apply(c));XCTAssertEqual(engine.resets,4);d.close()
    XCTAssertTrue(effects.clauses.isEmpty)
  }
  func testTransientKeywordIsConsumedBeforeNextDecodeOverwritesIt() {
    let c=testController();c.dispatch(.start);let t=c.token!,engine=KeywordFixture()
    engine.onDecode={ step in engine.result=step==1 ? "HEY EILO" : "" }
    let d=WakeDetector(configuration:config,verified:{true},open:{_ in engine});XCTAssertTrue(d.begin(t))
    XCTAssertTrue(process(d,t)!.apply(c));XCTAssertEqual(engine.decoded,2);XCTAssertEqual(engine.resets,1);d.close()
  }
  func testStopAndPrivacyRejectQueuedWakeAndCancelledInput() {
    for privacy:PrivacyChange? in [nil,.lock,.privateSession,.identityReset] {
      let c=testController();c.dispatch(.start);let t=c.token!,engine=KeywordFixture();engine.result="HEY EILO"
      let d=WakeDetector(configuration:config,verified:{true},open:{_ in engine});XCTAssertTrue(d.begin(t));let event=process(d,t)!
      if let privacy { c.privacyTransition(privacy) } else { c.stop() }
      XCTAssertFalse(event.apply(c));XCTAssertNil(process(d,t));XCTAssertEqual(engine.accepted,1);XCTAssertEqual(engine.closed,1)
    }
  }
  func testCancellationDuringDecodeAndRevokedPermissionRejectActivation() {
    let permission=FakePermission(),c=testController();c.dispatch(.start);let t=c.token!,engine=KeywordFixture();engine.result="HEY EILO"
    let d=WakeDetector(configuration:config,verified:{true},open:{_ in engine});d.begin(t);engine.onAccept={c.stop()};XCTAssertNil(process(d,t));XCTAssertEqual(engine.closed,1)
    let gated=testController(permission:permission);gated.dispatch(.start);let fresh=gated.token!;engine.onAccept=nil;engine.result="HEY EILO";d.begin(fresh);let event=process(d,fresh)!
    permission.value = .denied;XCTAssertFalse(event.apply(gated));XCTAssertEqual(gated.state,.stopped);d.close()
  }
  func testClosedOrReboundDetectorRejectsQueuedEventWithSameControllerToken() {
    let c=testController();c.dispatch(.start);let t=c.token!,engine=KeywordFixture();engine.result="HEY EILO"
    let d=WakeDetector(configuration:config,verified:{true},open:{_ in engine});d.begin(t);let event=process(d,t)!;d.close();XCTAssertFalse(event.apply(c))
    engine.result="HEY EILO";d.begin(t);let second=process(d,t)!;engine.result="HEY EILO";d.begin(t);XCTAssertFalse(second.apply(c));XCTAssertTrue(process(d,t)!.apply(c));d.close()
  }
  func testRestartClosesOldStreamWithoutOldInputPoisoningNewStream() {
    let c=testController();c.dispatch(.start);let old=c.token!,first=KeywordFixture(),second=KeywordFixture();var opens=0
    let d=WakeDetector(configuration:config,verified:{true},open:{_ in defer { opens += 1 };return opens==0 ? first : second });XCTAssertTrue(d.begin(old))
    c.stop();c.dispatch(.start);let fresh=c.token!;XCTAssertTrue(d.begin(fresh));XCTAssertEqual(first.closed,1)
    XCTAssertNil(process(d,old));XCTAssertEqual(second.closed,0);second.result="HEY EILO";XCTAssertTrue(process(d,fresh)!.apply(c));d.close()
  }
  func testRouteRateChangeClosesStreamAndRevokesPendingWake() {
    let c=testController();c.dispatch(.start);let old=c.token!,first=KeywordFixture(),second=KeywordFixture();var opens=0
    let d=WakeDetector(configuration:config,verified:{true},open:{_ in defer { opens += 1 };return opens==0 ? first : second })
    XCTAssertTrue(d.begin(old));first.result="HEY EILO";let event=process(d,old)!
    first.expectedRate=48000;first.result="HEY EILO"
    XCTAssertNil(pcm.withUnsafeBufferPointer { d.process(old,input:$0,sampleRate:48000) })
    XCTAssertEqual(first.accepted,1);XCTAssertEqual(first.closed,1);XCTAssertFalse(event.apply(c))
    XCTAssertTrue(first.borrowed!.allSatisfy {$0==0});XCTAssertNil(process(d,old));XCTAssertEqual(first.accepted,1)
    c.stop();c.dispatch(.start);let fresh=c.token!;second.expectedRate=48000;second.result="HEY EILO"
    XCTAssertTrue(d.begin(fresh));XCTAssertNil(process(d,old));XCTAssertEqual(second.closed,0)
    XCTAssertTrue(pcm.withUnsafeBufferPointer { d.process(fresh,input:$0,sampleRate:48000) }!.apply(c));d.close()
  }
  func testMissingVerificationAndRevocationFailClosed() {
    let c=testController();c.dispatch(.start);let t=c.token!;XCTAssertFalse(WakeDetector(configuration:config).begin(t))
    var verified=false,opens=0;let engine=KeywordFixture(),d=WakeDetector(configuration:config,verified:{verified},open:{_ in opens += 1;return engine})
    XCTAssertFalse(d.begin(t));XCTAssertEqual(opens,0);verified=true;XCTAssertTrue(d.begin(t));verified=false;XCTAssertNil(process(d,t));XCTAssertEqual(engine.closed,1)
  }
  func testBadInputBoundsAndNonfiniteSamplesCloseBeforeBackend() {
    let inputs:[[Float]]=[[],[.nan],[.infinity],[1.1],[Float](repeating:0,count:1601)]
    for input in inputs {
      let c=testController();c.dispatch(.start);let t=c.token!,engine=KeywordFixture(),d=WakeDetector(configuration:config,verified:{true},open:{_ in engine});d.begin(t)
      XCTAssertNil(input.withUnsafeBufferPointer { d.process(t,input:$0,sampleRate:16000) });XCTAssertEqual(engine.accepted,0);XCTAssertEqual(engine.closed,1)
    }
    for rate in [7999,192001] {
      let c=testController();c.dispatch(.start);let engine=KeywordFixture(),d=WakeDetector(configuration:config,verified:{true},open:{_ in engine});d.begin(c.token!)
      XCTAssertNil(pcm.withUnsafeBufferPointer { d.process(c.token!,input:$0,sampleRate:rate) });XCTAssertEqual(engine.accepted,0)
    }
  }
  func testBackendFailuresAndRunawayDecodeEraseAndClose() {
    for stage in ["accept","ready","decode","result","reset","endless"] {
      let c=testController();c.dispatch(.start);let t=c.token!,engine=KeywordFixture();engine.fail=stage;engine.endless=stage=="endless";engine.result="HEY EILO"
      let d=WakeDetector(configuration:config,verified:{true},open:{_ in engine});d.begin(t);XCTAssertNil(process(d,t));XCTAssertEqual(engine.closed,1);XCTAssertTrue(engine.borrowed!.allSatisfy {$0==0});XCTAssertLessThanOrEqual(engine.decoded,32);XCTAssertEqual(c.state,.standby)
    }
  }
  func testFailedReleaseDisablesReopenAndReportsOnlySafeMetadata() {
    let c=testController();c.dispatch(.start);let t=c.token!,engine=KeywordFixture(),diagnostics=SafeDiagnostics();var opens=0
    let d=WakeDetector(configuration:config,diagnostics:diagnostics,verified:{true},open:{_ in opens += 1;return engine});d.begin(t);engine.fail="close";d.close();XCTAssertFalse(d.begin(t));XCTAssertEqual(opens,1)
    XCTAssertEqual(diagnostics.snapshot(),[SafeDiagnostic(component:.model,code:.unavailable,severity:.error)])
  }
  func testInvalidConfigurationAndOpenFailureCannotActivate() {
    for phrase in ["","hey eilo","HEY\nEILO","HEY EILO ",String(repeating:"A",count:65)] { XCTAssertThrowsError(try WakeConfiguration(phrase:phrase,threshold:0.6,boost:1)) }
    for threshold:Float in [0,-1,.nan,.infinity,1.1] { XCTAssertThrowsError(try WakeConfiguration(phrase:"EILO",threshold:threshold,boost:1)) }
    for boost:Float in [0,.nan,11] { XCTAssertThrowsError(try WakeConfiguration(phrase:"EILO",threshold:0.6,boost:boost)) }
    let c=testController();c.dispatch(.start);XCTAssertFalse(WakeDetector(configuration:config,verified:{true}).begin(c.token!))
  }
}
