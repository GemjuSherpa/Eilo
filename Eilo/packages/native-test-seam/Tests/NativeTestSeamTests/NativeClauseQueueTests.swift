import XCTest
@testable import NativeTestSeam
final class NativeClauseQueueTests:XCTestCase {
  func testPresentationCardIdentitySurvivesNormalEndButChangesForANewQuery()throws{
    let c=controller(),s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}))
    XCTAssertEqual(c.spokenPresentation(allowed:true)["cardId"] as? String,"")
    q.enqueue("First.");q.enqueue("Second.");q.seal();s.callbacks[0](.finished)
    let first=try XCTUnwrap(c.spokenPresentation(allowed:true)["cardId"] as? String);XCTAssertNotNil(UUID(uuidString:first))
    s.callbacks[1](.finished);XCTAssertEqual(c.spokenPresentation(allowed:true)["cardId"] as? String,first)
    c.dispatch(.speechDetected,token:c.token);XCTAssertEqual(c.spokenPresentation(allowed:true)["cardId"] as? String,"")
    c.dispatch(.endpoint,token:c.token);let next=Sink();let q2=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:next,authorized:{_,_ in true}))
    q2.enqueue("New answer.");next.callbacks[0](.finished);XCTAssertNotEqual(c.spokenPresentation(allowed:true)["cardId"] as? String,first)
  }
  func testSdkInterruptionLabelsOnlyAnEmptyCompletedSpeechView()throws{
    let c=controller(),s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}))
    q.enqueue("Unfinished words.");s.callbacks[0](.started);s.callbacks[0](.interrupted)
    let result=c.spokenPresentation(allowed:true)
    XCTAssertEqual(result["interrupted"] as? Bool,true);XCTAssertEqual(result["clauses"] as? [String],[])
    c.stop();XCTAssertTrue(c.spokenPresentation(allowed:true).isEmpty)
  }
  func testDisabledPresentationCannotAccumulateOrResurrectCompletedText()throws{
    let c=controller(),s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}))
    c.setSpokenPresentationEnabled(false);q.enqueue("Hidden synthetic text.");s.callbacks[0](.finished)
    c.setSpokenPresentationEnabled(true);XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],[])
    q.enqueue("Visible completed text.");s.callbacks[1](.finished);XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],["Visible completed text."])
    c.setSpokenPresentationEnabled(false);c.setSpokenPresentationEnabled(true)
    XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],[])
  }
  func testPresentationContainsOnlySdkCompletedClausesAndSurvivesNormalTurnEnd()throws{
    let c=controller(),s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}))
    XCTAssertTrue(q.enqueue("Completed."));XCTAssertTrue(q.enqueue("Not finished."));XCTAssertTrue(q.seal())
    s.callbacks[0](.started);XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],[])
    s.callbacks[0](.finished);XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],["Completed."])
    XCTAssertTrue(c.spokenPresentation(allowed:false).isEmpty);XCTAssertNil(c.snapshot()["clauses"])
    s.callbacks[1](.finished);XCTAssertEqual(c.state,.standby)
    XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],["Completed.","Not finished."])
    XCTAssertTrue(c.dispatch(.speechDetected,token:c.token));XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],[])
  }
  func testPresentationStopLockAndPreferenceClearRejectLateCallbacks()throws{
    for locked in [false,true]{let c=controller(),s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}));q.enqueue("Only completed.");s.callbacks[0](.finished)
      c.clearSpokenPresentation();XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],[])
      q.enqueue("Never completed.");if locked{c.privacyTransition(.lock)}else{c.stop()};s.callbacks.last?(.finished)
      XCTAssertTrue(c.spokenPresentation(allowed:true).isEmpty)
    }
  }
  func testPresentationBoundsAndCancellationLabelDoNotReleasePartialClause()throws{
    let c=controller(),s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}))
    for i in 0..<8{q.enqueue(String(repeating:"x",count:900));s.callbacks[i](.finished)}
    let shown=c.spokenPresentation(allowed:true),clauses=try XCTUnwrap(shown["clauses"] as? [String])
    XCTAssertLessThanOrEqual(clauses.reduce(0,{$0+$1.utf8.count}),4096);XCTAssertEqual(shown["earlierClausesOmitted"] as? Bool,true)
    q.enqueue("Unfinished private suffix.");s.callbacks.last?(.started);q.cancel();s.callbacks.last?(.finished)
    XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],[])
    XCTAssertEqual(c.spokenPresentation(allowed:true)["interrupted"] as? Bool,true)
  }
  func testDismissIsVisualOnlySuppressesSameReplyAndRejectsStaleCard()throws{
    let c=controller(),s=Sink(),token=c.token!;let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:token,sink:s,authorized:{_,_ in true}))
    q.enqueue("First.");q.enqueue("Second.");q.seal();s.callbacks[0](.finished)
    let shown=c.spokenPresentation(allowed:true),session=try XCTUnwrap(shown["sessionId"] as? String),epoch=try XCTUnwrap(shown["privacyEpoch"] as? UInt64),card=try XCTUnwrap(shown["cardId"] as? String)
    XCTAssertFalse(c.dismissSpokenPresentation(session:session,epoch:epoch,card:card,onlyIdle:true))
    XCTAssertTrue(c.dismissSpokenPresentation(session:session,epoch:epoch,card:card));XCTAssertTrue(c.token===token);XCTAssertFalse(token.cancelled);XCTAssertEqual(s.stops,0)
    c.setSpokenPresentationEnabled(false);c.setSpokenPresentationEnabled(true);s.callbacks[1](.finished)
    XCTAssertEqual(c.state,.standby);XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],[])
    XCTAssertTrue(c.dispatch(.speechDetected,token:c.token));XCTAssertTrue(c.dispatch(.endpoint,token:c.token))
    let sink=Sink(),next=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:sink,authorized:{_,_ in true}));next.enqueue("New.");sink.callbacks[0](.finished)
    XCTAssertFalse(c.dismissSpokenPresentation(session:session,epoch:epoch,card:card));XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],["New."])
  }
  func testIdleDismissReleasesCompletedCardWithoutStoppingStandby()throws{
    let c=controller(),s=Sink(),q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}));q.enqueue("Done.");q.seal();s.callbacks[0](.finished)
    let v=c.spokenPresentation(allowed:true),token=c.token
    XCTAssertTrue(c.dismissSpokenPresentation(session:v["sessionId"] as! String,epoch:v["privacyEpoch"] as! UInt64,card:v["cardId"] as! String,onlyIdle:true))
    XCTAssertTrue(c.token===token);XCTAssertEqual(c.state,.standby);XCTAssertEqual(c.spokenPresentation(allowed:true)["clauses"] as? [String],[])
  }
  final class Sink:NativeClauseSink{
    var texts:[String]=[],callbacks:[(OfflineSpeechEvent)->Void]=[],stops=0,ok=true
    func enqueue(_ token:GenerationToken,text:String,event:@escaping(OfflineSpeechEvent)->Void)->Bool{texts.append(text);callbacks.append(event);return ok}
    func cancel(){stops+=1}
  }
  func controller()->NativeController{let c=NativeController(effects:LlmControllerJobTests.Effects(),permission:LlmControllerJobTests.Permission(),models:LlmControllerJobTests.Models());XCTAssertTrue(c.dispatch(.start));XCTAssertTrue(c.dispatch(.speechDetected,token:c.token));XCTAssertTrue(c.dispatch(.endpoint,token:c.token));c.setSpokenPresentationEnabled(true);return c}
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

  func testProgressDistinguishesStopRequestFromSdkCompletion()throws{let c=controller(),s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}))
    q.enqueue("First.");q.enqueue("Second.");s.callbacks[0](.started);XCTAssertTrue(q.progress().isEmpty);_ = c.stop();let records=q.progress{true};XCTAssertEqual(records.count,2);XCTAssertTrue(records[0].sdkStarted);XCTAssertTrue(records[0].interruptionRequested);XCTAssertFalse(records[0].sdkFinished);XCTAssertFalse(records[0].sdkInterrupted);XCTAssertTrue(records[1].discardedBeforeStart)
    s.callbacks[0](.finished);XCTAssertEqual(records,q.progress{true});_ = c.privacyTransition(.lock);XCTAssertTrue(q.progress{true}.isEmpty)
  }
  func testSdkCompletionAndInterruptionAreSeparate()throws{for event in [OfflineSpeechEvent.finished,.interrupted]{let c=controller(),s=Sink();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,authorized:{_,_ in true}));q.enqueue("First.");s.callbacks[0](.started);s.callbacks[0](event);let record=try XCTUnwrap(q.progress{true}.first);XCTAssertEqual(record.sdkFinished,event == .finished);XCTAssertEqual(record.sdkInterrupted,event == .interrupted)}}
  func testProgressLedgerIsBounded(){let ledger=PlaybackLedger();for _ in 0..<40{ledger.produced(UUID())};XCTAssertEqual(ledger.snapshot().count,32);XCTAssertTrue(ledger.snapshot().allSatisfy{$0.produced && $0.queued});ledger.clear();XCTAssertTrue(ledger.snapshot().isEmpty)}

  final class Timer:IdleScheduler{var fire:()->Void={};struct Cancel:IdleCancellation{func cancel(){}};func schedule(_ delayMilliseconds:UInt64,task:@escaping()->Void)->any IdleCancellation{XCTAssertEqual(delayMilliseconds,60_000);fire=task;return Cancel()}}
  func testMissingSdkCompletionTimesOutAndLateCallbacksCannotDrain()throws{let c=controller(),s=Sink(),timer=Timer();let q=try XCTUnwrap(NativeClauseQueue.create(controller:c,token:c.token!,sink:s,scheduler:timer,authorized:{_,_ in true}));q.enqueue("First.");q.enqueue("Second.");timer.fire();s.callbacks[0](.finished);XCTAssertEqual(s.texts,["First."]);XCTAssertGreaterThan(s.stops,0);XCTAssertEqual(c.state,.error);XCTAssertTrue(try XCTUnwrap(q.progress{true}.first).failed)}

  func testSpeechReceiverPublishesBeforeCancellationAndRechecksStop(){let c=controller();var published=false,cancelled=false;XCTAssertNotNil(c.prepareSpeechWork(c.token!,cancel:{XCTAssertTrue(published);cancelled=true},publish:{_ in published=true}));_ = c.stop();XCTAssertTrue(cancelled)
    let stopped=controller(),token=stopped.token!;XCTAssertNil(stopped.prepareSpeechWork(token,cancel:{},publish:{_ in _ = stopped.stop()}));XCTAssertTrue(token.cancelled)
  }

}
