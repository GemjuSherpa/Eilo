import XCTest
@testable import NativeTestSeam
final class StandbyAudioBufferTests:XCTestCase {
 private func append(_ b:StandbyAudioBuffer,_ ticket:UInt64,_ values:[Float]) { values.withUnsafeBufferPointer { b.append(ticket:ticket,input:$0) } }
 func testStreamKeepsOnlyTwoSecondsInOrderAcrossWraps() {
  var time:UInt64=0;let b=StandbyAudioBuffer(sampleRate:8000,now:{time});let ticket=b.begin()
  for frame in 0...5 { time=UInt64(frame)*500_000_000;append(b,ticket,Array(repeating:Float(frame),count:4000)) }
  XCTAssertEqual(b.count,16000);XCTAssertEqual(b.sample(0),2);XCTAssertEqual(b.sample(15999),5)
 }
 func testOversizedFrameKeepsSuffixAndDoesNotRetainCallerMemory() {
  let b=StandbyAudioBuffer(sampleRate:8000,now:{0});let ticket=b.begin();var input=(0..<20000).map(Float.init);append(b,ticket,input);input=Array(repeating:0,count:input.count)
  XCTAssertEqual(b.count,16000);XCTAssertEqual(b.sample(0),4000);XCTAssertEqual(b.sample(15999),19999)
 }
 func testExpiryAndClockRegressionFailClosed() {
  var time:UInt64=100;let b=StandbyAudioBuffer(sampleRate:8000,now:{time});let ticket=b.begin();append(b,ticket,[42])
  time+=1_999_999_999;XCTAssertEqual(b.count,1);time+=1;b.expire();XCTAssertEqual(b.count,0)
  append(b,ticket,[43]);time=0;XCTAssertEqual(b.count,0)
 }
 func testStopAndStaleCallbacksCannotRefillAnotherRun() {
  let b=StandbyAudioBuffer(sampleRate:8000,now:{0});let old=b.begin();append(b,old,[7]);b.close();append(b,old,[8]);XCTAssertEqual(b.count,0)
  let fresh=b.begin();append(b,fresh,[9]);append(b,old,[10]);XCTAssertEqual(b.count,1);XCTAssertEqual(b.sample(0),9)
  b.clear();XCTAssertEqual(b.count,0);append(b,fresh,[11]);XCTAssertEqual(b.sample(0),11)
 }
 func testNonfiniteSamplesAreZeroedAndLargeFramesClearOnClose() {
  let b=StandbyAudioBuffer(sampleRate:8000,now:{0});let ticket=b.begin();append(b,ticket,[.nan,.infinity,1]);XCTAssertEqual(b.sample(0),0);XCTAssertEqual(b.sample(1),0)
  append(b,ticket,Array(repeating:2,count:100000));b.close();XCTAssertEqual(b.count,0)
 }
}
