import XCTest
@testable import NativeTestSeam
final class RecognitionPolicyTests:XCTestCase {
  func testUncertainAmbiguousOverlapClarifyWithoutReleasingConversation(){for (score,ambiguous,overlap):(Float?,Bool,Bool) in [(nil,false,false),(0.3,false,false),(0.95,true,false),(0.95,false,true),(.nan,false,false)]{
    let effects=EffectsSpy(),c=testController(effects:effects);_ = c.dispatch(.start);_ = c.dispatch(.speechDetected,token:c.token);let t=c.token!
    XCTAssertTrue(c.finishRecognition(t,result:AsrText(text:"My name is Jemju Shurpa",final:true),confidence:score,ambiguous:ambiguous,overlap:overlap,active:{true},accepted:{_ in XCTFail()}))
    XCTAssertEqual(c.state,.speaking);XCTAssertFalse(c.finishRecognition(t,result:AsrText(text:"duplicate",final:true),confidence:0.95,active:{true},accepted:{_ in XCTFail()}))
  }}
  func testPartialStaleRevokedAndClearOnce(){let c=testController();_ = c.dispatch(.start);_ = c.dispatch(.speechDetected,token:c.token);let t=c.token!
    XCTAssertFalse(c.finishRecognition(t,result:AsrText(text:"question",final:false),confidence:0.95,active:{true},accepted:{_ in XCTFail()}))
    XCTAssertFalse(c.finishRecognition(t,result:AsrText(text:"question",final:true),confidence:0.95,active:{false},accepted:{_ in XCTFail()}))
    var received=[String]();XCTAssertTrue(c.finishRecognition(t,result:AsrText(text:"  what time is it  ",final:true),confidence:0.95,active:{true},accepted:{received.append($0)}));XCTAssertEqual(received,["what time is it"]);_ = c.stop()
    XCTAssertFalse(c.finishRecognition(t,result:AsrText(text:"stale",final:true),confidence:0.95,active:{true},accepted:{_ in XCTFail()}))
  }
}
