import XCTest
@testable import NativeTestSeam
final class ConfirmedSpeechInterruptionTests:XCTestCase {
  func testNoiseSelfPlaybackAndShortBurstCannotInterruptThenConfirmedSpeechCancels(){let time=FakeTime(),effects=EffectsSpy(),c=testController(effects:effects,clock:time,scheduler:time);var canceledAt:UInt64?;effects.onCancel={canceledAt=time.now}
    _ = c.dispatch(.start);_ = c.dispatch(.speechDetected,token:c.token);let old=c.token!;_ = c.dispatch(.endpoint,token:old);_ = c.releaseSpeech(old,clause:"reply");let d=ConfirmedSpeechInterruption(old)
    for _ in 0..<30{XCTAssertNil(d.advance(0.5,independentUserSpeech:true));XCTAssertNil(d.advance(0.95,independentUserSpeech:false))};for _ in 0..<7{XCTAssertNil(d.advance(0.95,independentUserSpeech:true))};XCTAssertNil(d.advance(0.05,independentUserSpeech:true));XCTAssertNil(canceledAt)
    for _ in 0..<7{time.now+=20;XCTAssertNil(d.advance(0.95,independentUserSpeech:true))};time.now+=20;let event=d.advance(0.95,independentUserSpeech:true)!
    XCTAssertNotNil(event.apply(c,independentSpeechStillVerified:{true}));XCTAssertEqual(canceledAt,160);XCTAssertTrue(old.cancelled);XCTAssertEqual(c.state,.capturing);XCTAssertFalse(c.releaseSpeech(old,clause:"stale"));XCTAssertEqual(effects.clauses,["reply"]);XCTAssertNil(event.apply(c,independentSpeechStillVerified:{true}))
  }
  func testRevocationAndReentrantStopCannotReplace(){let effects=EffectsSpy(),c=testController(effects:effects);_ = c.dispatch(.start);_ = c.dispatch(.speechDetected,token:c.token);let t=c.token!;_ = c.dispatch(.endpoint,token:t)
    XCTAssertNil(c.interruptReply(t,independentSpeechStillVerified:{false}));XCTAssertFalse(t.cancelled);effects.onCancel={_ = c.stop()};XCTAssertNil(c.interruptReply(t,independentSpeechStillVerified:{true}));XCTAssertEqual(c.state,.stopped);XCTAssertNil(c.token)
  }
}
