import XCTest
@testable import NativeTestSeam
final class FakeTime: NativeClock, IdleScheduler {
  var now: UInt64=0
  final class Job: IdleCancellation { let task: () -> Void; var cancelled=false; init(_ task: @escaping () -> Void) { self.task=task }; func cancel() { cancelled=true } }
  var jobs: [Job]=[]
  func milliseconds() -> UInt64 { now }
  func schedule(_ delayMilliseconds: UInt64,task: @escaping () -> Void) -> any IdleCancellation { let job=Job(task); jobs.append(job); return job }
}
final class IdleTimerTests: XCTestCase {
  func testProcessingPlaybackDeferAndSixtySecondsOfIdle() {
    let time=FakeTime(), spy=EffectsSpy(); let c=testController(effects:spy,clock:time,scheduler:time)
    c.dispatch(.start); XCTAssertTrue(time.jobs.isEmpty)
    c.dispatch(.speechDetected,token:c.token); c.dispatch(.endpoint,token:c.token)
    time.now=120_000; XCTAssertTrue(time.jobs.isEmpty); XCTAssertEqual(c.state,.thinking)
    c.releaseSpeech(c.token!,clause:"synthetic"); time.now=240_000; XCTAssertTrue(time.jobs.isEmpty)
    c.dispatch(.playbackFinished,token:c.token); let job=time.jobs.last!
    time.now += 59_999; job.task(); XCTAssertEqual(spy.cleared,0)
    time.now += 1; time.jobs.last!.task(); XCTAssertEqual(spy.cleared,1); XCTAssertEqual(spy.released,0)
    XCTAssertEqual(c.state,.standby); XCTAssertEqual(spy.committedHistory,[4,5])
  }
  func testResumedSpeechAndStopInvalidateOldTimers() {
    let time=FakeTime(), spy=EffectsSpy(); let c=testController(effects:spy,clock:time,scheduler:time)
    for e: ControllerEvent in [.start,.speechDetected,.endpoint,.speechReady,.playbackFinished] { c.dispatch(e,token:c.token) }
    let old=time.jobs.last!; c.dispatch(.speechDetected,token:c.token)
    XCTAssertTrue(old.cancelled); time.now=100_000; old.task(); XCTAssertEqual(c.state,.capturing); XCTAssertEqual(spy.cleared,0)
    c.stop(); old.task(); XCTAssertEqual(c.state,.stopped); XCTAssertEqual(spy.cleared,1)
  }
}
