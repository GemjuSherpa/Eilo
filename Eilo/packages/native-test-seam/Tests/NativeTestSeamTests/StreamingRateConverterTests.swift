import XCTest
@testable import NativeTestSeam

final class StreamingRateConverterTests:XCTestCase {
  func convert(_ input:[Float],sizes:[Int],rate:Int=48000)throws->[Float] {
    let c=try StreamingRateConverter(sourceRate:rate);var result=[Float](),offset=0,index=0
    while offset<input.count{let n=min(sizes[index%sizes.count],input.count-offset);try input.withUnsafeBufferPointer{try c.convert(UnsafeBufferPointer(rebasing:$0[offset..<offset+n])){result+=Array($0)}};offset+=n;index+=1}
    XCTAssertEqual(c.pendingSourceSamples,rate==48000 ? input.count%3:0);c.close();XCTAssertEqual(c.pendingSourceSamples,0);return result
  }
  func test16kPassThroughPreservesEveryFloatBit()throws {
    let input:[Float]=[0,-0.0,0.1234567,-1,1];let output=try convert(input,sizes:[1,2],rate:16000)
    XCTAssertEqual(output.map{$0.bitPattern},input.map{$0.bitPattern})
  }
  func test48kChunksPreservePhaseAndExactFloorDuration()throws {
    let input=(0..<4807).map{Float(sin(Double($0)*0.13)*0.5)}
    let a=try convert(input,sizes:[4800]),b=try convert(input,sizes:[1,2,5,511,7,320])
    XCTAssertEqual(a.count,1602);XCTAssertEqual(a,b)
  }
  func testFilterPassbandAndAliasRejectionOnStreamingTones()throws {
    func rms(_ hz:Double)throws->Double {
      let input=(0..<9600).map{Float(0.5*sin(2*Double.pi*hz*Double($0)/48000))}
      let output=try convert(input,sizes:[512,17,1,4800]).dropFirst(100)
      return sqrt(output.reduce(0){$0+Double($1)*Double($1)}/Double(output.count))
    }
    let pass=try rms(1000),stop=try rms(10000)
    XCTAssertEqual(pass,0.5/sqrt(2),accuracy:0.001);XCTAssertLessThan(stop/pass,0.0031623)
  }
  func testInvalidRateSamplesBoundsAndClosedStreamReject()throws {
    XCTAssertThrowsError(try StreamingRateConverter(sourceRate:44100))
    for input:[Float] in [[],[.nan],[1.1],Array(repeating:0,count:4801)] {
      let c=try StreamingRateConverter(sourceRate:48000)
      XCTAssertThrowsError(try input.withUnsafeBufferPointer{try c.convert($0){_ in XCTFail("invalid output")}})
      XCTAssertEqual(c.pendingSourceSamples,0)
      XCTAssertThrowsError(try [Float](repeating:0,count:3).withUnsafeBufferPointer{try c.convert($0){_ in XCTFail("revived")}})
    }
  }
  func testPartialTailIsNotPaddedAndConsumerFailureCloses()throws {
    let c=try StreamingRateConverter(sourceRate:48000);var calls=0
    try [Float](repeating:1,count:2).withUnsafeBufferPointer{try c.convert($0){_ in calls+=1}}
    XCTAssertEqual(calls,0);XCTAssertEqual(c.pendingSourceSamples,2);c.close();XCTAssertEqual(c.pendingSourceSamples,0)
    let failed=try StreamingRateConverter(sourceRate:48000)
    XCTAssertThrowsError(try [Float](repeating:0,count:3).withUnsafeBufferPointer{try failed.convert($0){_ in throw VadFailure.unavailable}})
    XCTAssertThrowsError(try [Float](repeating:0,count:3).withUnsafeBufferPointer{try failed.convert($0){_ in}})
  }
}
