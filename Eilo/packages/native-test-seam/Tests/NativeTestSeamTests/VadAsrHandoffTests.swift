import XCTest
@testable import NativeTestSeam

final class VadAsrHandoffTests:XCTestCase {
  final class Backend:AsrStream {
    var pcm=[Float](),closes=0,finals=0
    var onAccept:()->Void={},onFinal:()->Void={},onClose:()->Void={}
    func accept(_ input:UnsafeBufferPointer<Float>)throws{pcm+=Array(input);onAccept()}
    func text(finish:Bool)throws->String{if finish{finals+=1;onFinal()};return "synthetic question"}
    func close(){closes+=1;onClose()}
  }
  func token()->GenerationToken{let c=testController();_ = c.dispatch(.start);return c.token!}
  func append(_ h:VadAsrHandoff,count:Int=320,consumed:Int?=nil,start:Int,value:Float=0)->Bool {
    [Float](repeating:value,count:count).withUnsafeBufferPointer{h.append($0,consumed:consumed ?? count,startSample:start)}
  }
  func recognized(_ value:VadAsrFinal)->AsrText?{if case .recognized(let text)=value{return text};return nil}
  func testExactPrefixCopiesAndOneFinalExcludesUnusedSuffix() {
    let b=Backend();var opens=0;let h=VadAsrHandoff(token:token(),allowed:{true},open:{opens+=1;return b})
    for i in 0..<33{XCTAssertTrue(append(h,start:i*320,value:0.25))}
    var pcm=[Float](repeating:0.75,count:320)
    XCTAssertTrue(pcm.withUnsafeBufferPointer{h.append($0,consumed:192,startSample:10560)});pcm[0] = -1
    XCTAssertEqual(opens,0);XCTAssertEqual(h.retainedSamples,10752)
    let text=recognized(h.finish(VadCaptureOutcome(result:.complete,totalSamples:10752,lastChunkConsumed:192)))
    XCTAssertEqual(text?.text,"synthetic question");XCTAssertEqual(text?.final,true)
    XCTAssertEqual(b.pcm,Array(repeating:0.25,count:10560)+Array(repeating:0.75,count:192))
    XCTAssertEqual(opens,1);XCTAssertEqual(b.finals,1);XCTAssertEqual(b.closes,1);XCTAssertEqual(h.retainedSamples,0)
    XCTAssertNil(recognized(h.finish(VadCaptureOutcome(result:.complete,totalSamples:10752,lastChunkConsumed:192))))
  }
  func testSilenceAndIncompleteNeverOpenAsr() {
    for n in [0,7,80000] {
      var opens=0;let h=VadAsrHandoff(token:token(),allowed:{true},open:{opens+=1;return Backend()})
      var start=0;while start<n{let take=min(1600,n-start);XCTAssertTrue(append(h,count:take,start:start));start+=take}
      let r=h.finish(VadCaptureOutcome(result:n==80000 ? .noSpeech:.incomplete,totalSamples:n,lastChunkConsumed:0))
      if case .metadata=r{}else{XCTFail("metadata expected")}
      XCTAssertEqual(opens,0);XCTAssertEqual(h.retainedSamples,0)
    }
  }
  func testThirtySecondCapAndOverflowCannotExtendAudio() {
    let b=Backend(),h=VadAsrHandoff(token:token(),allowed:{true},open:{b})
    for start in stride(from:0,to:480000,by:1600){XCTAssertTrue(append(h,count:1600,start:start))}
    XCTAssertNotNil(recognized(h.finish(VadCaptureOutcome(result:.limit,totalSamples:480000,lastChunkConsumed:1600))))
    XCTAssertEqual(b.pcm.count,480000);XCTAssertEqual(b.closes,1)
    let overflow=VadAsrHandoff(token:token(),allowed:{true},open:{Backend()})
    for start in stride(from:0,to:480000,by:1600){XCTAssertTrue(append(overflow,count:1600,start:start))}
    XCTAssertFalse(append(overflow,count:1,start:480000));XCTAssertEqual(overflow.retainedSamples,0)
  }
  func testMalformedOrDiscontinuousInputTerminallyClears() {
    for (start,count,consumed,value):(Int,Int,Int,Float) in [(1,320,320,0),(0,320,0,0),(0,320,321,0),(0,1601,1601,0),(0,320,320,.nan)] {
      let h=VadAsrHandoff(token:token(),allowed:{true},open:{Backend()})
      XCTAssertFalse(append(h,count:count,consumed:consumed,start:start,value:value));XCTAssertEqual(h.retainedSamples,0)
      XCTAssertFalse(append(h,start:0))
    }
  }
  func testBadOutcomeCannotInventTextAndCloses() {
    for r:EndpointResult in [.continued,.invalid,.noSpeech,.limit] {
      var opens=0;let h=VadAsrHandoff(token:token(),allowed:{true},open:{opens+=1;return Backend()})
      XCTAssertTrue(append(h,start:0));XCTAssertNil(recognized(h.finish(VadCaptureOutcome(result:r,totalSamples:320,lastChunkConsumed:320))))
      XCTAssertEqual(opens,0);XCTAssertEqual(h.retainedSamples,0)
    }
  }
  func testRevocationAtAcceptFinalOrCleanupWithholdsText() {
    for phase in 0..<3 {
      var valid=true;let b=Backend(),h=VadAsrHandoff(token:token(),allowed:{valid},open:{b})
      for i in 0..<34{XCTAssertTrue(append(h,count:i==33 ? 192:320,start:i*320))}
      if phase==0{b.onAccept={valid=false}}else if phase==1{b.onFinal={valid=false}}else{b.onClose={valid=false}}
      XCTAssertNil(recognized(h.finish(VadCaptureOutcome(result:.complete,totalSamples:10752,lastChunkConsumed:192))))
      XCTAssertEqual(b.closes,1);XCTAssertEqual(h.retainedSamples,0)
    }
  }
  func testDefaultRevokedTokenAndCloseNeverOpen() {
    let c=testController();_ = c.dispatch(.start);let t=c.token!;_ = c.stop()
    let h=VadAsrHandoff(token:t,allowed:{true},open:{XCTFail("revoked open");return Backend()})
    XCTAssertFalse(append(h,start:0));XCTAssertEqual(h.retainedSamples,0)
    let denied=VadAsrHandoff(token:token(),allowed:{false},open:{Backend()});XCTAssertFalse(append(denied,start:0))
  }
}
