import XCTest
@testable import NativeTestSeam
final class PromptBudgetTests:XCTestCase {
  func count(_ text:String)->Int{text.utf8.count}
  func testTrimPreservesRulesLatestAndRecentContext()throws{let p=try PromptBudget.build(latest:"Latest request.",history:[QwenTurn(role:.user,text:String(repeating:"old",count:1800)),QwenTurn(role:.assistant,text:"Recent answer.")],recall:[String(repeating:"r",count:300),String(repeating:"s",count:300)],memoryAllowed:true,count:count)
    XCTAssertEqual(p.droppedHistory,1);XCTAssertEqual(p.droppedRecall,1);XCTAssertLessThanOrEqual(p.promptTokens+p.outputLimit,4096);XCTAssertLessThanOrEqual(p.recalledTokens,512);XCTAssertTrue(p.text.contains(QwenTemplate.rules));XCTAssertTrue(p.text.contains("Latest request."));XCTAssertTrue(p.text.contains("Recent answer."));XCTAssertFalse(p.text.contains("oldold"))
  }
  func testExactLimitsAndIrreducibleLatest()throws{let p=try PromptBudget.build(latest:"Latest.",recall:["Recall."],memoryAllowed:true,count:{$0.hasPrefix(UntrustedMemory.begin) ? 512:3840});XCTAssertEqual(p.recalledTokens,512);XCTAssertEqual(p.promptTokens+p.outputLimit,4096)
    XCTAssertThrowsError(try PromptBudget.build(latest:String(repeating:"x",count:4000),memoryAllowed:true,count:count));XCTAssertThrowsError(try PromptBudget.build(latest:"Latest.",outputLimit:257,memoryAllowed:true,count:count))
  }
  func testUnavailableInvalidAndOversizedRecall()throws{XCTAssertThrowsError(try PromptBudget.build(latest:"Latest."));XCTAssertThrowsError(try PromptBudget.build(latest:"Latest.",count:{_ in 0}));let p=try PromptBudget.build(latest:"Latest.",recall:Array(repeating:String(repeating:"r",count:600),count:32),memoryAllowed:true,count:count);XCTAssertEqual(p.droppedRecall,32);XCTAssertEqual(p.recalledTokens,0)}
  func testLoadedTokenizerGate()throws{let api=NativeLlmAPI(create:{OpaquePointer(bitPattern:7)},load:{_,_,_ in 0},begin:{_,_,_ in 0},next:{_,_,_ in 0},cancel:{_ in},destroy:{_ in},countTokens:{_,bytes in XCTAssertEqual(String(bytes:bytes,encoding:.utf8),"Generic fixture.");return 12});let stream=try NativeLlmStream(allowed:{true},api:api);defer{stream.close()};try stream.load(verifiedDescriptor:31);XCTAssertEqual(try stream.countTokens("Generic fixture."),12);stream.requestCancellation();XCTAssertThrowsError(try stream.countTokens("Late."))}
}
