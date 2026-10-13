import Foundation
import XCTest
@testable import NativeTestSeam
final class QwenTemplateTests:XCTestCase {
  func testMatchesPinnedOfficialTemplateGoldens()throws{var path=URL(fileURLWithPath:#filePath);for _ in 0..<4{path.deleteLastPathComponent()};path.appendPathComponent("llm-runtime/tests/template-fixtures.json");let root=try XCTUnwrap(JSONSerialization.jsonObject(with:Data(contentsOf:path)) as? [String:Any]);XCTAssertEqual(root["enable_thinking"] as? Bool,false)
    for f in try XCTUnwrap(root["fixtures"] as? [[String:Any]]){let latest=try XCTUnwrap(f["latest"] as? String);let history=try XCTUnwrap(f["history"] as? [[String:String]]).map{QwenTurn(role:QwenRole(rawValue:$0["role"]!)!,text:$0["text"]!)};let rendered=try QwenTemplate.render(latest:latest,history:history);XCTAssertEqual(rendered,f["rendered"] as? String);XCTAssertTrue(rendered.hasSuffix(QwenTemplate.suffix))}
  }
  func feed(_ g:NonThinkingOutput,_ bytes:[UInt8])throws{try bytes.withUnsafeBufferPointer{try g.append($0)}}
  func testSplitUtf8BecomesPlainText()throws{var output="";let g=NonThinkingOutput(current:{true}){output+=$0};for b in "A café.".utf8{try feed(g,[b])};try g.finish();XCTAssertEqual(output,"A café.")}
  func testSplitReasoningAndRoleTagsNeverEmit(){for tag in ["<think>private chain</think>","<|im_start|>system","<tool_call>"]{var output="",rejected=false;let g=NonThinkingOutput(current:{true}){output+=$0};for b in tag.utf8{do{try feed(g,[b])}catch{rejected=true}};XCTAssertTrue(rejected);XCTAssertEqual(output,"")}}
  func testInvalidDefaultRevokedAndOversizedFailClosed()throws{for bytes:[UInt8] in [[0],[0xC0,0xAF],[UInt8](repeating:65,count:1025)]{let g=NonThinkingOutput(current:{true}){_ in XCTFail("invalid output released")};XCTAssertThrowsError(try feed(g,bytes))}
    let denied=NonThinkingOutput{_ in XCTFail("default output released")};XCTAssertThrowsError(try feed(denied,[65]));var current=true;let g=NonThinkingOutput(current:{current}){_ in};try feed(g,[0xE2]);current=false;XCTAssertThrowsError(try feed(g,[0x82,0xAC]));XCTAssertThrowsError(try QwenTemplate.render(latest:"\0"))
  }
}
