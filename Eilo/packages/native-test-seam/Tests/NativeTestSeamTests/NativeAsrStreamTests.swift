import XCTest
@testable import NativeTestSeam
final class NativeAsrStreamTests:XCTestCase {
  func testLeaseRevokedDuringNativeDecodeCannotReleaseText(){var valid=true,closes=0;let h=OpaquePointer(bitPattern:1)!
    let api=NativeAsrAPI(create:{_ in h},accept:{_,_ in 0},text:{_,_,b in b[0]=65;b[1]=0;valid=false;return 0},destroy:{_ in closes+=1})
    let s=try! NativeAsrStream(directory:"/synthetic",verified:{valid},api:api);XCTAssertThrowsError(try s.text(finish:true));s.close();XCTAssertEqual(closes,1)
  }
  func testInvalidUtf8AndDefaultUnavailable(){XCTAssertThrowsError(try NativeAsrStream(directory:"/synthetic",verified:{true}));var closes=0
    let api=NativeAsrAPI(create:{_ in OpaquePointer(bitPattern:1)},accept:{_,_ in 0},text:{_,_,b in b[0]=CChar(bitPattern:0xc0);b[1]=CChar(bitPattern:0x80);b[2]=0;return 0},destroy:{_ in closes+=1})
    let s=try! NativeAsrStream(directory:"/synthetic",verified:{true},api:api);XCTAssertThrowsError(try s.text(finish:false));XCTAssertEqual(closes,1)
  }
}
