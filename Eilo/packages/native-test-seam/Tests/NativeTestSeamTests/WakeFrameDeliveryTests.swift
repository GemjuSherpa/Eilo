import XCTest
@testable import NativeTestSeam

private final class DeliveryEngine:WakeKeywordStream {
  var frames=[[Float]](),closed=0,result=""
  var borrowed:UnsafeBufferPointer<Float>?
  var acceptHook:(()->Void)?
  func accept(_ samples:UnsafeBufferPointer<Float>,sampleRate:Int) throws { borrowed=samples;frames.append(Array(samples));acceptHook?() }
  func ready() throws->Bool { false }
  func decode() throws { XCTFail("Unexpected decode") }
  func keyword() throws->String { result }
  func reset() throws { result="" }
  func close() throws { closed+=1 }
}
final class WakeFrameDeliveryTests:XCTestCase {
  private func delivery(_ c:NativeController,_ engine:DeliveryEngine,now:@escaping ()->UInt64={0}) throws->WakeFrameDelivery {
    c.dispatch(.start)
    let config=try WakeConfiguration(phrase:"HEY EILO",threshold:0.125,boost:1.5)
    let detector=WakeDetector(configuration:config,verified:{true},open:{_ in engine})
    return try WakeFrameDelivery(sampleRate:16000,detector:detector,token:c.token!,now:now)
  }
  private func submit(_ d:WakeFrameDelivery,_ values:[Float],rate:Int=16000)->Bool { values.withUnsafeBufferPointer {d.submit($0,sampleRate:rate)} }
  func testCallbackCopiesWithoutDecodingAndWorkerPreservesOrderErasesScratch() throws {
    let c=testController(),engine=DeliveryEngine(),d=try delivery(c,engine)
    var samples:[Float]=[0.25,0.5];XCTAssertTrue(submit(d,samples));samples[0]=0
    XCTAssertTrue(submit(d,[-0.5]));XCTAssertTrue(engine.frames.isEmpty)
    guard case .events(let events)=d.drain() else { return XCTFail("Drain failed") }
    XCTAssertTrue(events.isEmpty);XCTAssertEqual(engine.frames,[[0.25,0.5],[-0.5]])
    XCTAssertTrue(engine.borrowed!.allSatisfy {$0==0});d.close();XCTAssertEqual(engine.closed,1)
  }
  func testQueueOverflowNeverDropsFramesIntoAnExistingStream() throws {
    let c=testController(),engine=DeliveryEngine(),d=try delivery(c,engine)
    for _ in 0..<4 { XCTAssertTrue(submit(d,[0.1])) };XCTAssertFalse(submit(d,[0.2]))
    guard case .failed=d.drain() else { return XCTFail("Overflow not reported") }
    XCTAssertTrue(engine.frames.isEmpty);XCTAssertEqual(engine.closed,1)
    guard case .inactive=d.drain() else { return XCTFail("Failure repeated") };d.close()
  }
  func testInvalidFramesAndChangedRatesFailBeforeDecoder() throws {
    for values:[Float] in [[],[.nan],[1.1],Array(repeating:0,count:1601)] {
      let c=testController(),engine=DeliveryEngine(),d=try delivery(c,engine)
      XCTAssertFalse(submit(d,values));guard case .failed=d.drain() else { return XCTFail("Invalid frame accepted") }
      XCTAssertTrue(engine.frames.isEmpty);XCTAssertEqual(engine.closed,1)
    }
    let c=testController(),engine=DeliveryEngine(),d=try delivery(c,engine)
    XCTAssertFalse(submit(d,[0],rate:48000));guard case .failed=d.drain() else { return XCTFail("Rate change accepted") }
    XCTAssertTrue(engine.frames.isEmpty)
  }
  func testExpiredFramesAndClockRegressionCloseBeforeDecode() throws {
    for timeAfter:UInt64 in [250_000_100,99] {
      var time:UInt64=100;let c=testController(),engine=DeliveryEngine(),d=try delivery(c,engine,now:{time})
      XCTAssertTrue(submit(d,[0.1]));time=timeAfter
      guard case .failed=d.drain() else { return XCTFail("Stale frame accepted") };XCTAssertTrue(engine.frames.isEmpty)
    }
  }
  func testOverflowAfterDecodeRevokesQueuedActivation() throws {
    let c=testController(),engine=DeliveryEngine(),d=try delivery(c,engine)
    engine.result="HEY EILO";XCTAssertTrue(submit(d,[0]))
    guard case .events(let events)=d.drain(),events.count==1 else { return XCTFail("Missing wake") }
    for _ in 0..<4 { _=submit(d,[0]) };XCTAssertFalse(submit(d,[0]))
    XCTAssertFalse(events[0].apply(c));XCTAssertEqual(c.state,.standby);d.close()
  }
  func testStopAndPrivacyRejectDeliveryAndPendingWake() throws {
    for privacy:PrivacyChange? in [nil,.lock,.privateSession,.identityReset] {
      let c=testController(),engine=DeliveryEngine(),d=try delivery(c,engine)
      engine.result="HEY EILO";XCTAssertTrue(submit(d,[0]))
      guard case .events(let events)=d.drain(),events.count==1 else { return XCTFail("Missing wake") }
      if let privacy {c.privacyTransition(privacy)} else {c.stop()};d.close()
      XCTAssertFalse(events[0].apply(c));XCTAssertFalse(submit(d,[0]));XCTAssertEqual(engine.closed,1)
    }
  }
  func testFreshCaptureSlotRejectsLateAttachmentAndOldDelivery() throws {
    let c=testController(),engine=DeliveryEngine(),d=try delivery(c,engine),old=WakeCaptureSlot(sampleRate:16000)
    old.close();XCTAssertFalse(old.attach(d))
    let fresh=WakeCaptureSlot(sampleRate:16000);XCTAssertTrue(fresh.attach(d));XCTAssertFalse(fresh.attach(d))
    [Float(0.5)].withUnsafeBufferPointer { old.submit($0,sampleRate:16000) };XCTAssertTrue(engine.frames.isEmpty)
    [Float(0.25)].withUnsafeBufferPointer { fresh.submit($0,sampleRate:16000) };_ = fresh.drain()
    XCTAssertEqual(engine.frames,[[0.25]]);fresh.close();fresh.close();XCTAssertEqual(engine.closed,1)
  }
  func testStopWaitsForBorrowedDecodeAndErasesBeforeReturning() throws {
    let c=testController(),engine=DeliveryEngine(),d=try delivery(c,engine)
    let entered=DispatchSemaphore(value:0),release=DispatchSemaphore(value:0),drained=DispatchSemaphore(value:0),closed=DispatchSemaphore(value:0)
    engine.acceptHook={entered.signal();_ = release.wait(timeout:.now()+5)}
    XCTAssertTrue(submit(d,[0.5]))
    DispatchQueue.global().async { _=d.drain();drained.signal() }
    XCTAssertEqual(entered.wait(timeout:.now()+2),.success)
    DispatchQueue.global().async { d.close();closed.signal() }
    XCTAssertEqual(closed.wait(timeout:.now()+0.02),.timedOut)
    release.signal();XCTAssertEqual(closed.wait(timeout:.now()+2),.success);XCTAssertEqual(drained.wait(timeout:.now()+2),.success)
    XCTAssertTrue(engine.borrowed!.allSatisfy {$0==0});XCTAssertEqual(engine.closed,1);XCTAssertFalse(submit(d,[0]))
  }
  func testDetachAllowsFreshGenerationWithoutReopeningCaptureSlot() throws {
    let c=testController(),first=DeliveryEngine(),d=try delivery(c,first),slot=WakeCaptureSlot(sampleRate:16000)
    XCTAssertTrue(slot.attach(d));slot.detach();XCTAssertEqual(first.closed,1)
    c.stop();let second=DeliveryEngine(),fresh=try delivery(c,second)
    XCTAssertTrue(slot.attach(fresh));[Float(0.5)].withUnsafeBufferPointer {slot.submit($0,sampleRate:16000)};_ = slot.drain()
    XCTAssertEqual(second.frames,[[0.5]]);slot.close()
  }
}
