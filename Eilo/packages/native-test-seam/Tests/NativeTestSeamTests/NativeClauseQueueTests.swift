import XCTest
@testable import NativeTestSeam
final class NativeClauseQueueTests:XCTestCase {
  final class Sink:NativeClauseSink{
    var texts:[String]=[],callbacks:[(OfflineSpeechEvent)->Void]=[],stops=0,ok=true
    func enqueue(_ token:GenerationToken,text:String,event:@escaping(OfflineSpeechEvent)->Void)->Bool{texts.append(text);callbacks.append(event);return ok}
    func cancel(){stops+=1}
  }
  func controller()->NativeController{let c=NativeController(effects:LlmControllerJobTests.Effects(),permission:LlmControllerJobTests.Permission(),models:LlmControllerJobTests.Models());XCTAssertTrue(c.dispatch(.start));XCTAssertTrue(c.dispatch(.speechDetected,token:c.token));XCTAssertTrue(c.dispatch(.endpoint,token:c.token));return c}
  func testOrderGapAndSealOnlyEndAfterLastClause()throws{let c=controller(),t=c.token!,s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:t,sink:s,authorized:{_,_ in true}))
    XCTAssertTrue(q.enqueue("First."));XCTAssertTrue(q.enqueue("Second."));XCTAssertTrue(q.seal());XCTAssertEqual(s.texts,["First."])
    s.callbacks[0](.started);XCTAssertEqual(c.state,.speaking);s.callbacks[0](.finished);XCTAssertTrue(c.token===t);XCTAssertEqual(s.texts,["First.","Second."])
    s.callbacks[0](.finished);XCTAssertTrue(c.token===t);s.callbacks[1](.started);s.callbacks[1](.finished);XCTAssertEqual(c.state,.standby);XCTAssertTrue(t.cancelled)
  }
  func testStopClearsAndLateCallbackCannotStartNext()throws{let c=controller(),s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}))
    XCTAssertTrue(q.enqueue("First."));XCTAssertTrue(q.enqueue("Second."));c.stop();s.callbacks[0](.finished);XCTAssertEqual(s.texts,["First."]);XCTAssertGreaterThan(s.stops,0);XCTAssertFalse(q.enqueue("Late."));XCTAssertEqual(c.state,.stopped)
  }
  func testOverflowAndDefaultDeniedFailClosed()throws{for denied in [false,true]{let c=controller(),s=Sink();let q=try XCTUnwrap(denied ? NativeClauseQueue.create(controller:c,token:c.token!,sink:s):NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}))
    if denied{XCTAssertFalse(q.enqueue("Denied."));XCTAssertTrue(s.texts.isEmpty)}else{for _ in 0..<5{XCTAssertTrue(q.enqueue("Clause."))};XCTAssertFalse(q.enqueue("Overflow."));XCTAssertEqual(s.texts.count,1)};XCTAssertGreaterThan(s.stops,0);XCTAssertEqual(c.state,.error)
  }}
  func testAuthorizationRecheckedBeforeDrainAndSinkFailure()throws{let c=controller(),s=Sink();var allowed=true;let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in allowed}))
    XCTAssertTrue(q.enqueue("First."));XCTAssertTrue(q.enqueue("Second."));allowed=false;s.callbacks[0](.finished);XCTAssertEqual(s.texts.count,1);XCTAssertEqual(c.state,.error)
    let c2=controller(),bad=Sink();bad.ok=false;let q2=try XCTUnwrap(NativeClauseQueue.create(controller:c2,token:c2.token!,sink:bad,authorized:{_,_ in true}));XCTAssertFalse(q2.enqueue("Failure."));XCTAssertEqual(c2.state,.error)
  }
  func testLlmRemainsAllowedDuringPlaybackAndGap()throws{let c=controller(),t=c.token!,s=Sink();let llm=try XCTUnwrap(c.prepareLlmWork(t,cancel:{}));let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:t,sink:s,authorized:{_,_ in true}))
    XCTAssertTrue(q.enqueue("First."));s.callbacks[0](.started);XCTAssertTrue(c.llmWorkAllowed(llm));s.callbacks[0](.finished);XCTAssertEqual(c.state,.thinking);XCTAssertTrue(c.llmWorkAllowed(llm));q.cancel();XCTAssertFalse(c.llmWorkAllowed(llm))
  }
  func testFragmentedNaturalClausesAndOversizeAreBounded()throws{let c=controller(),s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}))
    XCTAssertTrue(q.append("Value 1."));XCTAssertTrue(q.append("5 is fine. Next"));XCTAssertEqual(s.texts,["Value 1.5 is fine."]);XCTAssertTrue(q.append(" clause!"));XCTAssertTrue(q.seal());s.callbacks[0](.finished);XCTAssertEqual(s.texts,["Value 1.5 is fine.","Next clause!"])
    let c2=controller(),s2=Sink();let q2=try XCTUnwrap(NativeClauseQueue.create(controller:c2,token:c2.token!,sink:s2,authorized:{_,_ in true}));XCTAssertTrue(q2.append(String(repeating:"x",count:1024)));XCTAssertFalse(q2.append("y"));XCTAssertTrue(s2.texts.isEmpty)
  }

}
