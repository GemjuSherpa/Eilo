import XCTest
@testable import NativeTestSeam
final class PlaybackRejectionTests:XCTestCase {
  func testKnownOutputAndTailCannotReopenTurn(){let time=FakeTime(),c=testController(clock:time,scheduler:time);_ = c.dispatch(.start);_ = c.dispatch(.speechDetected,token:c.token);let t=c.token!;_ = c.dispatch(.endpoint,token:t);XCTAssertTrue(c.releaseSpeech(t,clause:"Hey Eilo, can you hear me?"));XCTAssertFalse(c.recognitionAllowed(t));XCTAssertTrue(c.dispatch(.playbackFinished,token:t));let standby=c.token!
    XCTAssertFalse(c.wakeDetected(standby,active:{true}));time.now=299;XCTAssertFalse(c.wakeDetected(standby,active:{true}));time.now=300;XCTAssertTrue(c.wakeDetected(standby,active:{true}))
  }
  func testOldFinishCannotReleaseNewPlaybackAndRollbackFailsClosed(){let c=testController();_ = c.dispatch(.start);let old=c.token!;_ = c.dispatch(.speechDetected,token:old);let current=c.token!;var now:UInt64=100;let p=PlaybackRejection(now:{now});p.begin(current);XCTAssertFalse(p.finish(old));XCTAssertFalse(p.allowsAudio);XCTAssertTrue(p.finish(current));now=400;XCTAssertTrue(p.allowsAudio);now=399;XCTAssertFalse(p.allowsAudio)}
}
