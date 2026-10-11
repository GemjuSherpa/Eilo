import XCTest
@testable import NativeTestSeam
final class WakeQuestionHandoffTests:XCTestCase {
 func testCombinedQuestionAndOverlappingFramesAreDeliveredExactlyOnce(){
  let c=testController();_ = c.dispatch(.start);let h=WakeQuestionHandoff();var received:[Float]=[],calls=0
  XCTAssertTrue([Float](arrayLiteral:0.1,0.2,0.3,0.4,0.5).withUnsafeBufferPointer{h.offer($0,startSample:0)});XCTAssertEqual(calls,0)
  _ = c.dispatch(.speechDetected,token:c.token);let t=c.token!
  XCTAssertTrue(h.activate(t,firstQuestionSample:2,allowed:{!t.cancelled},consume:{received+=Array($0);calls+=1}))
  XCTAssertEqual(received,[0.3,0.4,0.5])
  XCTAssertTrue([Float](arrayLiteral:0.4,0.5,0.6,0.7).withUnsafeBufferPointer{h.offer($0,startSample:3)})
  XCTAssertTrue([Float](arrayLiteral:0.6,0.7).withUnsafeBufferPointer{h.offer($0,startSample:5)})
  XCTAssertEqual(received,[0.3,0.4,0.5,0.6,0.7]);XCTAssertEqual(calls,2);h.close()
 }
 func testBoundStopAndGap(){
  let c=testController();_ = c.dispatch(.start);let t=c.token!,h=WakeQuestionHandoff()
  for i in 0..<30{XCTAssertTrue([Float](repeating:0.1,count:1600).withUnsafeBufferPointer{h.offer($0,startSample:UInt64(i*1600))})}
  XCTAssertEqual(h.retainedSamples,32000);_ = c.stop();XCTAssertFalse(h.activate(t,firstQuestionSample:nil,allowed:{true},consume:{_ in XCTFail()}));h.close();XCTAssertEqual(h.retainedSamples,0)
  let gap=WakeQuestionHandoff();_ = [Float](arrayLiteral:0.1).withUnsafeBufferPointer{gap.offer($0,startSample:0)}
  XCTAssertFalse([Float](arrayLiteral:0.2).withUnsafeBufferPointer{gap.offer($0,startSample:2)})
 }
}
