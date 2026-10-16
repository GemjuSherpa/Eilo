import XCTest
@testable import NativeTestSeam
final class ProtectedKeyTests:XCTestCase {
  func testExactSizeAndClosedKeyCannotBeBorrowed()throws {
    XCTAssertThrowsError(try ProtectedKey([1]))
    let key=try ProtectedKey([UInt8](repeating:7,count:32));var reads=0
    try key.borrow{XCTAssertEqual(Array($0),[UInt8](repeating:7,count:32));reads+=1}
    key.close();key.close();XCTAssertFalse(key.active)
    let erased=Mirror(reflecting:key).children.first{$0.label=="bytes"}?.value as? [UInt8]
    XCTAssertEqual(erased,[UInt8](repeating:0,count:32))
    XCTAssertThrowsError(try key.borrow{_ in reads+=1});XCTAssertEqual(reads,1)
  }
}
