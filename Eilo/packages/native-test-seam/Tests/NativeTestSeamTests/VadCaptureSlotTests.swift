import XCTest
@testable import NativeTestSeam

final class VadCaptureSlotTests:XCTestCase {
  typealias Worker=VadCaptureTransportTests.Worker
  typealias Backend=VadCaptureTransportTests.Backend
  func submit(_ slot:VadCaptureSlot,count:Int=320) {
    [Float](repeating:0,count:count).withUnsafeBufferPointer{slot.submit($0,sampleRate:16000)}
  }
  func capturing(_ effects:any ControllerEffects)->NativeController {
    let c=testController(effects:effects);XCTAssertTrue(c.dispatch(.start));XCTAssertTrue(c.dispatch(.speechDetected,token:c.token));return c
  }
  func testDefaultDenialWrongCaptureAndNonCapturingTokenNeverOpen() {
    let w=Worker(),e=EffectsSpy(),slot=VadCaptureSlot(sampleRate:16000),c=capturing(EffectsSpy())
    var opens=0
    XCTAssertFalse(slot.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true},open:{_ in opens+=1;return Backend()}))
    let own=capturing(e)
    XCTAssertFalse(slot.install(capture:e,controller:own,token:own.token!,schedule:w.schedule,open:{_ in opens+=1;return Backend()}))
    let standby=testController(effects:e);_ = standby.dispatch(.start)
    XCTAssertFalse(slot.install(capture:e,controller:standby,token:standby.token!,schedule:w.schedule,verified:{true}))
    w.run();XCTAssertEqual(opens,0)
  }
  func testEofOnlyReleasesMetadataOnceWhileCapturingAndRevokesPermit() {
    let w=Worker(),e=EffectsSpy(),b=Backend(),slot=VadCaptureSlot(sampleRate:16000),c=capturing(e)
    var events=[VadCaptureOutcome]()
    XCTAssertTrue(slot.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true},open:{_ in b},accepted:{events.append($0)}))
    submit(slot,count:7);slot.finish();w.run();XCTAssertEqual(events.count,1)
    XCTAssertEqual(events[0].result,.incomplete);XCTAssertEqual(events[0].totalSamples,7)
    XCTAssertEqual(c.state,.capturing);XCTAssertEqual(b.closes,1)
    slot.finish();w.run();XCTAssertEqual(events.count,1)
    XCTAssertTrue(slot.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true}));slot.close();w.run()
  }
  func testStopPausePrivacyInterruptionAndStateExitRejectQueuedWork() {
    for phase in 0..<5 {
      let w=Worker(),e=EffectsSpy(),slot=VadCaptureSlot(sampleRate:16000),c=capturing(e)
      let token=c.token!;var opens=0,events=0
      XCTAssertTrue(slot.install(capture:e,controller:c,token:token,schedule:w.schedule,verified:{true},open:{_ in opens+=1;return Backend()},accepted:{_ in events+=1}))
      submit(slot,count:512)
      switch phase {
      case 0: _=c.stop()
      case 1: _=c.dispatch(.pause)
      case 2: _=c.privacyTransition(.lock)
      case 3: _=AudioInterruptionHandler(c).receive(.engineReset)
      default: _=c.dispatch(.endpoint,token:token)
      }
      w.run();XCTAssertEqual(opens,0);XCTAssertEqual(events,0)
    }
  }
  func testModelRevokedDuringActualProcessingFailsSafelyAndCloses() {
    let w=Worker(),e=EffectsSpy(),b=Backend(),slot=VadCaptureSlot(sampleRate:16000),c=capturing(e)
    var verified=true,events=0;b.processing={verified=false}
    XCTAssertTrue(slot.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{verified},open:{_ in b},accepted:{_ in events+=1}))
    submit(slot,count:512);w.run();XCTAssertEqual(events,0);XCTAssertEqual(b.closes,1)
    XCTAssertEqual(c.state,.error);XCTAssertEqual(c.error,.unavailable)
  }
  func testDetachedAndClosedSlotCannotAttachLateOrUseOldGeneration() {
    let w=Worker(),e=EffectsSpy(),b=Backend(),slot=VadCaptureSlot(sampleRate:16000),c=capturing(e)
    let old=c.token!
    XCTAssertTrue(slot.install(capture:e,controller:c,token:old,schedule:w.schedule,verified:{true},open:{_ in b}))
    submit(slot,count:512);w.run();slot.detach();XCTAssertEqual(b.closes,0);w.run();XCTAssertEqual(b.closes,1)
    _=c.stop();_ = c.dispatch(.start);_ = c.dispatch(.speechDetected,token:c.token)
    XCTAssertFalse(slot.install(capture:e,controller:c,token:old,schedule:w.schedule,verified:{true}))
    slot.close();XCTAssertFalse(slot.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true}));w.run()
  }
  func testStopWhileInferenceBlockedDoesNotWaitOrReleaseOutcome() {
    let inference=DispatchQueue(label:"test.vad.capture"),entered=DispatchSemaphore(value:0),release=DispatchSemaphore(value:0)
    let done=expectation(description:"worker cleanup"),e=EffectsSpy(),c=capturing(e),slot=VadCaptureSlot(sampleRate:16000)
    let b=Backend();b.processing={entered.signal();_ = release.wait(timeout:.now()+5)}
    XCTAssertTrue(slot.install(capture:e,controller:c,token:c.token!,schedule:{inference.async(execute:$0)},verified:{true},open:{_ in b},accepted:{_ in XCTFail("stale outcome")}))
    submit(slot,count:512);XCTAssertEqual(entered.wait(timeout:.now()+5),.success)
    XCTAssertTrue(c.stop());release.signal()
    inference.async {XCTAssertEqual(b.closes,1);done.fulfill()};wait(for:[done],timeout:5)
  }
  func testUnsupportedRouteAndSetupRevocationNeverAttach() {
    let w=Worker(),e=EffectsSpy(),c=capturing(e)
    XCTAssertFalse(VadCaptureSlot(sampleRate:44100).install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true}))
    let slot=VadCaptureSlot(sampleRate:16000);var checks=0
    XCTAssertFalse(slot.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{checks+=1;if checks==2{slot.close()};return true}))
    w.run();XCTAssertEqual(c.state,.capturing)
  }
}
