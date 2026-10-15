import XCTest
@testable import NativeTestSeam

final class VadCaptureTransportTests: XCTestCase {
  final class Worker {
    var tasks=[()->Void]()
    func schedule(_ task:@escaping ()->Void) { tasks.append(task) }
    func run() { while !tasks.isEmpty { tasks.removeFirst()() } }
  }
  final class Backend:VadStream {
    var pcm=[Float](),closes=0,calls=0
    var probability:Float=0.95
    var processing:()->Void={}
    func process(_ input:UnsafeBufferPointer<Float>,final:Bool)throws->NativeVadObservation {
      let start=pcm.count;pcm+=Array(input);calls+=1;processing()
      return NativeVadObservation(probability:probability,startSample:start,samples:input.count,final:final)
    }
    func close(){closes+=1}
  }
  func feed(_ d:VadCaptureTransport,count:Int=320,value:Float=0,rate:Int=16000)->Bool {
    [Float](repeating:value,count:count).withUnsafeBufferPointer { d.submit($0,sampleRate:rate) }
  }
  func testCopiesBorrowedFramesCoalescesWorkAndFinalizesActualTail() {
    let w=Worker(),b=Backend();var outcomes=[VadCaptureOutcome](),opens=0
    let d=VadCaptureTransport(schedule:w.schedule,verified:{true},open:{opens+=1;return b},output:{outcomes.append($0);XCTAssertTrue($1())})
    var pcm=[Float](repeating:0.25,count:320)
    XCTAssertTrue(pcm.withUnsafeBufferPointer{d.submit($0,sampleRate:16000)});pcm[0] = -0.5
    XCTAssertTrue(feed(d,count:7,value:0.75));d.finish()
    XCTAssertEqual(w.tasks.count,1);XCTAssertEqual(opens,0);XCTAssertEqual(d.retainedSamples,327)
    w.run();XCTAssertEqual(b.pcm,Array(repeating:0.25,count:320)+Array(repeating:0.75,count:7))
    XCTAssertEqual(outcomes.count,1);XCTAssertEqual(outcomes.first?.result,.incomplete)
    XCTAssertEqual(outcomes.first?.totalSamples,327);XCTAssertEqual(b.closes,1);XCTAssertEqual(d.retainedSamples,0)
  }
  func testOverflowIsTerminalAndErasesWithoutOpening() {
    let w=Worker();var opens=0,outputs=0
    let d=VadCaptureTransport(schedule:w.schedule,verified:{true},open:{opens+=1;return Backend()},output:{_,_ in outputs+=1})
    for _ in 0..<4 { XCTAssertTrue(feed(d,count:1600)) }
    XCTAssertEqual(d.retainedSamples,6400);XCTAssertFalse(feed(d));XCTAssertEqual(d.retainedSamples,0)
    XCTAssertEqual(w.tasks.count,1);w.run();XCTAssertEqual(opens,0);XCTAssertEqual(outputs,0)
    XCTAssertFalse(feed(d));XCTAssertFalse(d.current())
  }
  func testUnsupportedRatesMalformedSamplesAndClockRegressionRevoke() {
    for kind in 0..<5 {
      let w=Worker();var time:UInt64=100
      let d=VadCaptureTransport(schedule:w.schedule,verified:{true},now:{time})
      XCTAssertTrue(feed(d));time=kind==4 ? 99:100
      switch kind {
      case 0:XCTAssertFalse(feed(d,rate:48000))
      case 1:XCTAssertFalse(feed(d,count:1601))
      case 2:XCTAssertFalse(feed(d,value:.nan))
      case 3:XCTAssertFalse(feed(d,count:0))
      default:XCTAssertFalse(feed(d))
      }
      XCTAssertEqual(d.retainedSamples,0);w.run();XCTAssertFalse(d.current())
    }
  }
  func testAgeDeadlineAndDeniedLeaseDoNotOpen() {
    for revoked in [false,true] {
      let w=Worker();var time:UInt64=0,opens=0
      let d=VadCaptureTransport(schedule:w.schedule,verified:{!revoked},open:{opens+=1;return Backend()},now:{time})
      XCTAssertTrue(feed(d,count:512));if !revoked {time=250_000_000};w.run()
      XCTAssertEqual(opens,0);XCTAssertFalse(d.current());XCTAssertEqual(d.retainedSamples,0)
    }
  }
  func testStopWithoutMoreFramesSchedulesCleanupWithoutInlineDestruction() {
    let w=Worker(),b=Backend();let d=VadCaptureTransport(schedule:w.schedule,verified:{true},open:{b})
    XCTAssertTrue(feed(d,count:512));w.run();XCTAssertEqual(b.calls,1);XCTAssertEqual(b.closes,0)
    XCTAssertTrue(feed(d));d.close();XCTAssertEqual(d.retainedSamples,0);XCTAssertEqual(b.closes,0)
    XCTAssertEqual(w.tasks.count,1);w.run();XCTAssertEqual(b.closes,1);XCTAssertFalse(feed(d))
  }
  func testStopDuringInferenceSuppressesOutputAndNeverRevives() {
    let w=Worker(),b=Backend();var outputs=0
    let d=VadCaptureTransport(schedule:w.schedule,verified:{true},open:{b},output:{_,_ in outputs+=1})
    b.processing={d.close()}
    XCTAssertTrue(feed(d,count:512));w.run();XCTAssertEqual(outputs,0);XCTAssertEqual(b.closes,1)
    XCTAssertFalse(feed(d));XCTAssertEqual(d.retainedSamples,0)
  }
  func testEndpointReportsExactPrefixAndRechecksDelayedOutcomeLease() {
    let w=Worker(),b=Backend();var outcomes=[VadCaptureOutcome]();var current:(()->Bool)?
    let d=VadCaptureTransport(schedule:w.schedule,verified:{true},open:{b},output:{outcomes.append($0);current=$1})
    for i in 0..<34 { b.probability=i<8 ? 0.95:0.05;XCTAssertTrue(feed(d));w.run() }
    XCTAssertEqual(outcomes.count,1);XCTAssertEqual(outcomes[0].result,.complete)
    XCTAssertEqual(outcomes[0].totalSamples,10752);XCTAssertEqual(outcomes[0].lastChunkConsumed,192)
    XCTAssertTrue(current?() ?? false);d.close();XCTAssertFalse(current?() ?? true);w.run()
    XCTAssertEqual(b.pcm.count,10752);XCTAssertEqual(b.closes,1)
  }
}
