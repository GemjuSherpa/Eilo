import XCTest
@testable import NativeTestSeam
final class StreamingAsrTests:XCTestCase {
  final class Backend:AsrStream {
    var calls=0,closes=0,result="what time is it";var during:()->Void={}
    func accept(_ pcm:UnsafeBufferPointer<Float>) throws{calls+=1;XCTAssertEqual(pcm[0],0.5)}
    func text(finish:Bool)throws->String{during();return result}
    func close(){closes+=1}
  }
  func testOnlyActiveAudioOpensAndFinalIsOnce(){let c=testController();_ = c.dispatch(.start);let b=Backend();var opened=0;let a=StreamingAsr(c.token!,allowed:{true},open:{opened+=1;return b});XCTAssertEqual(opened,0);XCTAssertTrue([Float](arrayLiteral:0.5).withUnsafeBufferPointer{a.accept($0)});XCTAssertEqual(a.poll()?.text,"what time is it");XCTAssertTrue(a.poll(finish:true)!.final);XCTAssertNil(a.poll());XCTAssertEqual(b.closes,1)}
  func testStopDuringFinalAndOutputBounds(){let c=testController();_ = c.dispatch(.start);let b=Backend(),a=StreamingAsr(c.token!,allowed:{true},open:{b});_ = [Float](arrayLiteral:0.5).withUnsafeBufferPointer{a.accept($0)};b.during={_ = c.stop();_ = c.dispatch(.start)};XCTAssertNil(a.poll(finish:true));XCTAssertEqual(b.closes,1)
    let oversized=Backend();oversized.result=String(repeating:"x",count:4097);let other=StreamingAsr(c.token!,allowed:{true},open:{oversized});_ = [Float](arrayLiteral:0.5).withUnsafeBufferPointer{other.accept($0)};XCTAssertNil(other.poll());XCTAssertEqual(oversized.closes,1)
  }
  func testRevocationInvalidSamplesAndThirtySecondCap(){let c=testController();_ = c.dispatch(.start);var opened=0;let b=Backend(),denied=StreamingAsr(c.token!,allowed:{false},open:{opened+=1;return b});XCTAssertFalse([Float](arrayLiteral:0.5).withUnsafeBufferPointer{denied.accept($0)});XCTAssertEqual(opened,0)
    let a=StreamingAsr(c.token!,allowed:{true},open:{b});for _ in 0..<300{XCTAssertTrue([Float](repeating:0.5,count:1600).withUnsafeBufferPointer{a.accept($0)})};XCTAssertFalse([Float](arrayLiteral:0.5).withUnsafeBufferPointer{a.accept($0)});XCTAssertEqual(b.closes,1)
    let invalid=StreamingAsr(c.token!,allowed:{true},open:{XCTFail();return b});XCTAssertFalse([Float](arrayLiteral:.nan).withUnsafeBufferPointer{invalid.accept($0)})
  }
}
