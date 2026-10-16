import XCTest
@testable import NativeTestSeam

final class VadAsrCaptureTests:XCTestCase {
  typealias Worker=VadCaptureTransportTests.Worker
  typealias Vad=VadCaptureTransportTests.Backend
  typealias Asr=VadAsrHandoffTests.Backend
  func controller(_ e:EffectsSpy)->NativeController {let c=testController(effects:e);_ = c.dispatch(.start);_ = c.dispatch(.speechDetected,token:c.token);return c}
  func feed(_ s:VadCaptureSlot,count:Int=320,value:Float=0.25){[Float](repeating:value,count:count).withUnsafeBufferPointer{s.submit($0,sampleRate:16000)}}
  func testNativeJoinedPrefixOneFinalAndUnknownConfidenceStillClarifies() {
    let w=Worker(),e=EffectsSpy(),c=controller(e),v=Vad(),a=Asr(),s=VadCaptureSlot(sampleRate:16000)
    var finals=[AsrText](),events=[VadCaptureOutcome](),opens=0
    XCTAssertTrue(s.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true},open:{_ in v},accepted:{events.append($0)},openAsr:{_ in opens+=1;return a},recognized:{finals.append($0)},asrVerified:{true}))
    for i in 0..<34{v.probability=i<8 ? 0.95:0.05;feed(s);w.run();if i<33{XCTAssertEqual(opens,0)}}
    XCTAssertEqual(a.pcm,Array(repeating:0.25,count:10752));XCTAssertEqual(opens,1);XCTAssertEqual(a.closes,1)
    XCTAssertEqual(finals.count,1);XCTAssertEqual(events[0].lastChunkConsumed,192)
    XCTAssertTrue(c.finishRecognition(c.token!,result:finals[0],confidence:nil,active:{true},accepted:{_ in XCTFail("confidence must not be invented")}))
    XCTAssertEqual(e.clauses,[RecognitionPolicy.clarification]);s.close();w.run()
  }
  func testSilenceAndEofDoNotOpenAsrOrReleaseText() {
    for silence in [false,true] {
      let w=Worker(),e=EffectsSpy(),c=controller(e),v=Vad(),s=VadCaptureSlot(sampleRate:16000);var opens=0,finals=0
      v.probability=0.05
      XCTAssertTrue(s.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true},open:{_ in v},openAsr:{_ in opens+=1;return Asr()},recognized:{_ in finals+=1},asrVerified:{true}))
      if silence{for _ in 0..<250{feed(s);w.run()}}else{feed(s,count:7);s.finish();w.run()}
      XCTAssertEqual(opens,0);XCTAssertEqual(finals,0);s.close();w.run()
    }
  }
  func testStopAtAsrAcceptFinalOrCleanupCannotReleaseText() {
    for phase in 0..<3 {
      let w=Worker(),e=EffectsSpy(),c=controller(e),v=Vad(),a=Asr(),s=VadCaptureSlot(sampleRate:16000);var finals=0
      let stop={_ = c.stop()};if phase==0{a.onAccept=stop}else if phase==1{a.onFinal=stop}else{a.onClose=stop}
      XCTAssertTrue(s.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true},open:{_ in v},openAsr:{_ in a},recognized:{_ in finals+=1},asrVerified:{true}))
      for i in 0..<34{v.probability=i<8 ? 0.95:0.05;feed(s);w.run()}
      XCTAssertEqual(finals,0);XCTAssertEqual(a.closes,1);XCTAssertEqual(c.state,.stopped);s.close();w.run()
    }
  }
  func testIndependentAsrCapabilityRequiredAndRevokedAfterCleanup() {
    let w=Worker(),e=EffectsSpy(),c=controller(e),v=Vad(),a=Asr(),s=VadCaptureSlot(sampleRate:16000)
    XCTAssertFalse(s.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true},open:{_ in v},openAsr:{_ in a}))
    var valid=true,finals=0;a.onClose={valid=false}
    XCTAssertTrue(s.install(capture:e,controller:c,token:c.token!,schedule:w.schedule,verified:{true},open:{_ in v},openAsr:{_ in a},recognized:{_ in finals+=1},asrVerified:{valid}))
    for i in 0..<34{v.probability=i<8 ? 0.95:0.05;feed(s);w.run()}
    XCTAssertEqual(finals,0);XCTAssertEqual(c.state,.error);XCTAssertEqual(a.closes,1);s.close();w.run()
  }
  func testStopDoesNotWaitForBlockedAsrWorker() {
    let worker=DispatchQueue(label:"test.asr.blocked"),entered=DispatchSemaphore(value:0),release=DispatchSemaphore(value:0)
    let done=expectation(description:"ASR worker cleanup"),e=EffectsSpy(),c=controller(e),v=Vad(),a=Asr(),s=VadCaptureSlot(sampleRate:16000)
    var finals=0;a.onAccept={entered.signal();_ = release.wait(timeout:.now()+5)}
    XCTAssertTrue(s.install(capture:e,controller:c,token:c.token!,schedule:{worker.async(execute:$0)},verified:{true},open:{_ in v},openAsr:{_ in a},recognized:{_ in finals+=1},asrVerified:{true}))
    for i in 0..<33{v.probability=i<8 ? 0.95:0.05;feed(s);worker.sync{}}
    feed(s);XCTAssertEqual(entered.wait(timeout:.now()+5),.success);XCTAssertTrue(c.stop());release.signal()
    worker.async{XCTAssertEqual(finals,0);XCTAssertEqual(a.closes,1);done.fulfill()};wait(for:[done],timeout:5)
  }
}
