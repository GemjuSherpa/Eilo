import XCTest
@testable import NativeTestSeam

final class NativeWakeStreamTests:XCTestCase {
  private let pointer=OpaquePointer(bitPattern:1)!
  private var paths:WakeModelPaths { try! WakeModelPaths(encoder:"/verified/encoder",decoder:"/verified/decoder",joiner:"/verified/joiner",tokens:"/verified/tokens") }
  private var config:WakeConfiguration { try! WakeConfiguration(phrase:"HEY EILO",threshold:0.125,boost:1.5) }
  func testNativeHandleMapsOnlyWakeAndClosesExactlyOnce() throws {
    var creates=0,processes=0,destroys=0,result:Int32=1
    let api=NativeWakeAPI(create:{ p,c in creates += 1;XCTAssertEqual(p.tokens,"/verified/tokens");XCTAssertEqual(c.threshold,0.125);XCTAssertEqual(c.boost,1.5);return self.pointer },process:{ h,s,r in processes += 1;XCTAssertEqual(h,self.pointer);XCTAssertEqual(Array(s),[0.5]);XCTAssertEqual(r,16000);return result },destroy:{ _ in destroys += 1 })
    var stream:NativeWakeStream?=try NativeWakeStream(paths:paths,configuration:config,verified:{true},api:api)
    try [Float(0.5)].withUnsafeBufferPointer { try stream!.accept($0,sampleRate:16000) }
    XCTAssertFalse(try stream!.ready());XCTAssertEqual(try stream!.keyword(),"HEY EILO")
    try stream!.reset();result=0;try [Float(0.5)].withUnsafeBufferPointer { try stream!.accept($0,sampleRate:16000) }
    XCTAssertEqual(try stream!.keyword(),"");stream!.close();stream!.close();stream=nil
    XCTAssertEqual(creates,1);XCTAssertEqual(processes,2);XCTAssertEqual(destroys,1)
  }
  func testTrustRevocationBeforeAndDuringOpenCannotLeakHandle() {
    var valid=false,creates=0,destroys=0
    let api=NativeWakeAPI(create:{ _,_ in creates += 1;valid=false;return self.pointer },process:{ _,_,_ in XCTFail("Unverified input reached C");return 0 },destroy:{ _ in destroys += 1 })
    XCTAssertThrowsError(try NativeWakeStream(paths:paths,configuration:config,verified:{valid},api:api));XCTAssertEqual(creates,0)
    valid=true;XCTAssertThrowsError(try NativeWakeStream(paths:paths,configuration:config,verified:{valid},api:api));XCTAssertEqual(creates,1);XCTAssertEqual(destroys,1)
  }
  func testNativeFailureOrRevocationClearsResultAndDisablesFurtherInput() throws {
    for code:Int32 in [-1,2,1] {
      var valid=true,processes=0,destroys=0
      let api=NativeWakeAPI(create:{ _,_ in self.pointer },process:{ _,_,_ in processes += 1;if code==1 { valid=false };return code },destroy:{ _ in destroys += 1 })
      let s=try NativeWakeStream(paths:paths,configuration:config,verified:{valid},api:api)
      XCTAssertThrowsError(try [Float(0)].withUnsafeBufferPointer { try s.accept($0,sampleRate:16000) })
      XCTAssertThrowsError(try s.keyword());XCTAssertEqual(destroys,1)
      XCTAssertThrowsError(try [Float(0)].withUnsafeBufferPointer { try s.accept($0,sampleRate:16000) });XCTAssertEqual(processes,1)
    }
  }
  func testInvalidInputAndRateChangeNeverReachC() throws {
    for input:[Float] in [[],[.nan],[1.1],[Float](repeating:0,count:1601)] {
      var processes=0,destroys=0
      let api=NativeWakeAPI(create:{ _,_ in self.pointer },process:{ _,_,_ in processes += 1;return 0 },destroy:{ _ in destroys += 1 })
      let s=try NativeWakeStream(paths:paths,configuration:config,verified:{true},api:api)
      XCTAssertThrowsError(try input.withUnsafeBufferPointer { try s.accept($0,sampleRate:16000) });XCTAssertEqual(processes,0);XCTAssertEqual(destroys,1)
    }
    var processes=0,destroys=0
    let api=NativeWakeAPI(create:{ _,_ in self.pointer },process:{ _,_,_ in processes += 1;return 1 },destroy:{ _ in destroys += 1 })
    let s=try NativeWakeStream(paths:paths,configuration:config,verified:{true},api:api)
    try [Float(0)].withUnsafeBufferPointer { try s.accept($0,sampleRate:16000) }
    XCTAssertThrowsError(try [Float(0)].withUnsafeBufferPointer { try s.accept($0,sampleRate:48000) });XCTAssertEqual(processes,1);XCTAssertEqual(destroys,1);XCTAssertThrowsError(try s.keyword())
  }
  func testConfigurationPathsAndMissingLibraryFailClosed() {
    for path in ["relative", "", "/encoder\0ignored", "/"+String(repeating:"a",count:4096)] {
      XCTAssertThrowsError(try WakeModelPaths(encoder:path,decoder:"/d",joiner:"/j",tokens:"/t"))
    }
    let wrong=try! WakeConfiguration(phrase:"OTHER",threshold:0.125,boost:1.5)
    let api=NativeWakeAPI(create:{ _,_ in XCTFail("Unsupported phrase reached C");return self.pointer },process:{ _,_,_ in 0 },destroy:{ _ in })
    XCTAssertThrowsError(try NativeWakeStream(paths:paths,configuration:wrong,verified:{true},api:api))
    #if !canImport(CEiloWake)
    XCTAssertThrowsError(try NativeWakeStream(paths:paths,configuration:config,verified:{true}))
    #endif
    XCTAssertThrowsError(try NativeWakeStream(paths:paths,configuration:config,verified:{true},api:NativeWakeAPI(create:{ _,_ in nil },process:{ _,_,_ in 0 },destroy:{ _ in XCTFail("Null handle destroyed") })))
  }
  func testDeinitializationReleasesNativeHandle() throws {
    var destroys=0
    let api=NativeWakeAPI(create:{ _,_ in self.pointer },process:{ _,_,_ in 0 },destroy:{ _ in destroys += 1 })
    var s:NativeWakeStream?=try NativeWakeStream(paths:paths,configuration:config,verified:{true},api:api)
    XCTAssertNotNil(s);s=nil;XCTAssertEqual(destroys,1)
  }
}
