import XCTest
@testable import NativeTestSeam

final class RateCaptureTests:XCTestCase {
  typealias Worker=VadCaptureTransportTests.Worker
  typealias Backend=VadCaptureTransportTests.Backend
  func feed(_ d:VadCaptureTransport,count:Int,rate:Int=48000)->Bool {[Float](repeating:0,count:count).withUnsafeBufferPointer{d.submit($0,sampleRate:rate)}}
  func test48kQuietHasExactlyFiveNormalizedSeconds() {
    let w=Worker(),b=Backend();b.probability=0.05;var events=[VadCaptureOutcome]()
    let d=VadCaptureTransport(schedule:w.schedule,verified:{true},open:{b},output:{events.append($0);XCTAssertTrue($1())},sourceRate:48000)
    for _ in 0..<500{XCTAssertTrue(feed(d,count:480));w.run()}
    XCTAssertEqual(events.count,1);XCTAssertEqual(events[0].result,.noSpeech);XCTAssertEqual(events[0].totalSamples,80000)
    XCTAssertEqual(b.pcm.count,80000);XCTAssertEqual(b.closes,1);XCTAssertEqual(d.retainedSamples,0);d.close();w.run()
  }
  func testRawTailIsNotPaddedOrInventedAsEvidence() {
    for n in [1,2,7,4807] {
      let w=Worker(),b=Backend();var events=[VadCaptureOutcome]()
      let d=VadCaptureTransport(schedule:w.schedule,verified:{true},open:{b},output:{value,_ in events.append(value)},sourceRate:48000)
      var start=0;while start<n{let count=min(4800,n-start);XCTAssertTrue(feed(d,count:count));w.run();start+=count}
      d.finish();w.run();XCTAssertEqual(events[0].result,.incomplete);XCTAssertEqual(events[0].totalSamples,n/3)
      XCTAssertEqual(b.pcm.count,n/3);d.close();w.run()
    }
  }
  func testRateChangeAndRawQueueOverflowRevoke() {
    let w=Worker(),b=Backend();var failures=0
    let d=VadCaptureTransport(schedule:w.schedule,verified:{true},open:{b},failure:{_ in failures+=1},sourceRate:48000)
    XCTAssertTrue(feed(d,count:1536));w.run();XCTAssertEqual(b.calls,1)
    XCTAssertFalse(feed(d,count:320,rate:16000));w.run();XCTAssertEqual(b.closes,1);XCTAssertEqual(failures,1)
    let overflow=VadCaptureTransport(schedule:w.schedule,verified:{true},sourceRate:48000)
    for _ in 0..<4{XCTAssertTrue(feed(overflow,count:4800))};XCTAssertEqual(overflow.retainedSamples,19200)
    XCTAssertFalse(feed(overflow,count:1));XCTAssertEqual(overflow.retainedSamples,0);w.run()
  }
  func test48kSlotFeedsNormalizedAsrPrefixAndPreservesConfidenceGate() {
    let w=Worker(),e=EffectsSpy(),b=Backend(),a=VadAsrHandoffTests.Backend(),s=VadCaptureSlot(sampleRate:48000)
    let c=testController(effects:e);_ = c.dispatch(.start);_ = c.dispatch(.speechDetected,token:c.token)
    var finals=[AsrText](),events=[VadCaptureOutcome]()
    XCTAssertTrue(s.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true},open:{_ in b},accepted:{events.append($0)},openAsr:{_ in a},recognized:{finals.append($0)},asrVerified:{true}))
    for i in 0..<34{b.probability=i<8 ? 0.95:0.05;[Float](repeating:0,count:960).withUnsafeBufferPointer{s.submit($0,sampleRate:48000)};w.run()}
    XCTAssertEqual(finals.count,1);XCTAssertEqual(a.pcm.count,10752);XCTAssertEqual(events[0].lastChunkConsumed,192)
    XCTAssertTrue(c.finishRecognition(c.token!,result:finals[0],confidence:nil,active:{true},accepted:{_ in XCTFail("confidence invented")}))
    XCTAssertEqual(e.clauses,[RecognitionPolicy.clarification]);s.close();w.run()
  }
}
