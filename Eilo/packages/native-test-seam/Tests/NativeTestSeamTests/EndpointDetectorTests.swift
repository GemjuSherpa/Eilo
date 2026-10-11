import XCTest
@testable import NativeTestSeam
final class EndpointDetectorTests:XCTestCase {
 func testSpeechAndExactSilenceEndpoint(){let d=EndpointDetector();for _ in 0..<7{XCTAssertEqual(d.advance(0.95),.continued);XCTAssertFalse(d.confirmedSpeech)};_ = d.advance(0.95);XCTAssertTrue(d.confirmedSpeech);for _ in 0..<24{XCTAssertEqual(d.advance(0.05),.continued)};XCTAssertEqual(d.advance(0.05),.complete);XCTAssertEqual(d.advance(0.95),.invalid)}
 func testNoiseOverlapAndLimit(){for p:Float in [0.05,0.5]{let d=EndpointDetector();for _ in 0..<249{XCTAssertEqual(d.advance(p),.continued)};XCTAssertEqual(d.advance(p),.noSpeech)};let d=EndpointDetector();for _ in 0..<1499{XCTAssertEqual(d.advance(0.95),.continued)};XCTAssertEqual(d.advance(0.95),.limit);XCTAssertEqual(d.elapsedSamples,480000)}
 func testInvalidFrame(){XCTAssertEqual(EndpointDetector().advance(.nan),.invalid);XCTAssertEqual(EndpointDetector().advance(0.9,samples:160),.invalid)}
}
