import XCTest
@testable import NativeTestSeam

final class VadWindowDeliveryTests: XCTestCase {
  private final class Backend: VadStream {
    var received = [Float](), counts = [Int](), finals = [Bool](), closes = 0
    var onProcess: () -> Void = {}
    var onClose: () -> Void = {}
    var probability: Float = 0.95
    var wrongFrame = false
    func process(_ pcm: UnsafeBufferPointer<Float>, final: Bool) throws -> NativeVadObservation {
      let start = received.count
      received += Array(pcm); counts.append(pcm.count); finals.append(final); onProcess()
      return NativeVadObservation(probability: probability, startSample: wrongFrame ? start + 1 : start,
                                  samples: pcm.count, final: final)
    }
    func close() { closes += 1; onClose() }
  }
  private func feed(_ delivery: VadWindowDelivery, _ count: Int = 320, start: Int, value: Float = 0) -> VadDeliveryEvent {
    [Float](repeating: value,count:count).withUnsafeBufferPointer { delivery.accept($0,startSample:start) }
  }
  func testChunksAreCopiedInOrderAndOnlyRealTailIsFinalized() {
    let backend = Backend(); var opens = 0
    let delivery = VadWindowDelivery(allowed:{true},open:{opens += 1; return backend})
    var expected = [Float]()
    for chunk in 0..<20 {
      var pcm = (0..<320).map { Float((chunk*320+$0)%1000)/1000 }
      expected += pcm
      let event = pcm.withUnsafeBufferPointer { delivery.accept($0,startSample:chunk*320) }
      XCTAssertEqual(event.result,.continued);XCTAssertEqual(event.consumedSamples,320)
      pcm = [Float](repeating:-0.9,count:320)
      XCTAssertLessThan(delivery.retainedSamples,512)
    }
    XCTAssertEqual(opens,1);XCTAssertEqual(delivery.retainedSamples,256)
    XCTAssertEqual(delivery.finish().result,.incomplete)
    XCTAssertEqual(backend.received,expected)
    XCTAssertEqual(backend.counts,Array(repeating:512,count:12)+[256])
    XCTAssertEqual(backend.finals,Array(repeating:false,count:12)+[true])
    XCTAssertEqual(delivery.retainedSamples,0);XCTAssertEqual(backend.closes,1)
    delivery.close();XCTAssertEqual(backend.closes,1)
  }
  func testSilenceBudgetIsExactlyFiveSecondsWithOne128SampleTail() {
    let backend=Backend();backend.probability=0.05
    let d=VadWindowDelivery(allowed:{true},open:{backend})
    for i in 0..<249 { XCTAssertEqual(feed(d,start:i*320).result,.continued) }
    let event=feed(d,start:79680)
    XCTAssertEqual(event.result,.noSpeech);XCTAssertEqual(event.consumedSamples,320)
    XCTAssertEqual(d.acceptedSamples,80000);XCTAssertEqual(backend.counts.count,157)
    XCTAssertEqual(backend.counts.last,128);XCTAssertEqual(backend.finals.last,true)
    XCTAssertEqual(backend.received.count,80000);XCTAssertEqual(backend.closes,1)
  }
  func testEndpointConsumesOnlyThePrefixOfTheLastCaptureCallback() {
    let b=Backend();let d=VadWindowDelivery(allowed:{true},open:{b})
    for i in 0..<33 {
      b.probability=i<8 ? 0.95 : 0.05
      XCTAssertEqual(feed(d,start:i*320).result,.continued)
    }
    let event=feed(d,start:10560)
    XCTAssertEqual(event.result,.complete);XCTAssertEqual(event.consumedSamples,192)
    XCTAssertEqual(d.acceptedSamples,10752);XCTAssertEqual(b.received.count,10752)
    XCTAssertEqual(feed(d,start:10752).result,.invalid);XCTAssertEqual(b.closes,1)
  }
  func testContinuousSpeechStopsAtThirtySecondsWithoutAnExtraWindow() {
    let b=Backend();let d=VadWindowDelivery(allowed:{true},open:{b})
    for i in 0..<1499 { XCTAssertEqual(feed(d,start:i*320).result,.continued) }
    XCTAssertEqual(feed(d,start:479680).result,.limit)
    XCTAssertEqual(b.received.count,480000);XCTAssertEqual(b.counts.last,256)
    XCTAssertEqual(b.closes,1);XCTAssertEqual(d.retainedSamples,0)
  }
  func testRevocationClearsPendingBeforeOpeningAndNeverRevives() {
    var valid=true,opens=0;let b=Backend()
    let d=VadWindowDelivery(allowed:{valid},open:{opens += 1;return b})
    XCTAssertEqual(feed(d,start:0).result,.continued);XCTAssertEqual(d.retainedSamples,320)
    valid=false;XCTAssertEqual(feed(d,start:320).result,.invalid)
    XCTAssertEqual(d.retainedSamples,0);XCTAssertEqual(opens,0)
    valid=true;XCTAssertEqual(feed(d,start:320).result,.invalid)
    let denied=VadWindowDelivery()
    XCTAssertEqual(feed(denied,start:0).result,.invalid);XCTAssertEqual(denied.retainedSamples,0)
  }
  func testRevocationAtOpenDecodeOrBeforeInputCannotReleaseEvents() {
    for phase in 0..<3 {
      var valid=true;let b=Backend()
      if phase==1 { b.onProcess={valid=false} }
      let d=VadWindowDelivery(allowed:{valid},open:{if phase==0 {valid=false};return b})
      if phase==2 { valid=false }
      let event=feed(d,512,start:0)
      XCTAssertEqual(event.result,.invalid);XCTAssertEqual(event.consumedSamples,0)
      XCTAssertEqual(d.retainedSamples,0);XCTAssertEqual(b.closes,phase==2 ? 0:1)
    }
  }
  func testInvalidOrDiscontinuousInputAndBadNativeFrameAreTerminal() {
    for (start,count,value): (Int,Int,Float) in [(1,320,0),(0,0,0),(0,1601,0),(0,320,.nan),(0,320,1.1)] {
      let b=Backend();let d=VadWindowDelivery(allowed:{true},open:{b})
      XCTAssertEqual(feed(d,count,start:start,value:value).result,.invalid)
      XCTAssertEqual(d.retainedSamples,0);XCTAssertTrue(b.received.isEmpty)
    }
    let b=Backend();b.wrongFrame=true
    let d=VadWindowDelivery(allowed:{true},open:{b})
    XCTAssertEqual(feed(d,512,start:0).result,.invalid);XCTAssertEqual(b.closes,1)
    let duplicate=VadWindowDelivery(allowed:{true},open:{Backend()})
    _=feed(duplicate,start:0);XCTAssertEqual(feed(duplicate,start:0).result,.invalid)
  }
  func testEmptyEofAndExactWindowEofDoNotInventTailFrames() {
    var opens=0;let b=Backend();let empty=VadWindowDelivery(allowed:{true},open:{opens += 1;return b})
    XCTAssertEqual(empty.finish().result,.incomplete);XCTAssertEqual(opens,0)
    let full=VadWindowDelivery(allowed:{true},open:{b})
    XCTAssertEqual(feed(full,512,start:0).result,.continued)
    XCTAssertEqual(full.finish().result,.incomplete);XCTAssertEqual(b.counts,[512]);XCTAssertEqual(b.finals,[false])
    XCTAssertEqual(full.finish().result,.invalid);XCTAssertEqual(b.closes,1)
  }
  func testRevocationDuringCleanupWithholdsFinalEvent() {
    var valid=true;let b=Backend();let d=VadWindowDelivery(allowed:{valid},open:{b})
    XCTAssertEqual(feed(d,7,start:0).result,.continued)
    b.onClose={valid=false}
    XCTAssertEqual(d.finish().result,.invalid)
    XCTAssertEqual(d.retainedSamples,0);XCTAssertEqual(b.closes,1)
    valid=true;XCTAssertEqual(d.finish().result,.invalid)
  }

}
