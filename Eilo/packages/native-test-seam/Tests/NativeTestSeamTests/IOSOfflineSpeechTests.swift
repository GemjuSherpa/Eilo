import XCTest
@testable import NativeTestSeam
final class IOSOfflineSpeechTests:XCTestCase {
  final class Driver:IOSSpeechBackend {
    var values=[OfflineVoice(id:"en-au",language:"en-AU",installed:true,networkRequired:nil,offlineVerified:true)]
    var receive:(UUID,OfflineSpeechEvent)->Void={_,_ in},starts=0,stops=0,closes=0,id=UUID(),accepted=true
    func voices()->[OfflineVoice]{values};func listener(_ receive:@escaping(UUID,OfflineSpeechEvent)->Void){self.receive=receive}
    func start(id:UUID,text:String,voice:OfflineVoice,rate:Float,gain:Float)->Bool{self.id=id;starts+=1;XCTAssertEqual(text,"Generic fixture.");XCTAssertEqual(voice.id,"en-au");return accepted}
    func stop(){stops+=1};func shutdown(){closes+=1}
  }
  final class Queue{var work:[()->Void]=[];func schedule(_ task:@escaping()->Void){work.append(task)};func drain(){while !work.isEmpty{work.removeFirst()()}}}
  func token()->GenerationToken {
    let c=NativeController(effects:LlmControllerJobTests.Effects(),permission:LlmControllerJobTests.Permission(),models:LlmControllerJobTests.Models())
    XCTAssertTrue(c.dispatch(.start));return c.token!
  }
  func ready(_ d:Driver,_ q:Queue)->IOSOfflineSpeech{let a=IOSOfflineSpeech(backend:d,allowed:{!$0.cancelled},schedule:q.schedule);a.refresh{XCTAssertTrue($0)};q.drain();return a}
  func testExactVerifiedVoiceAsynchronousPlaybackAndMetadata(){let d=Driver(),q=Queue(),a=ready(d,q),t=token();var events:[OfflineSpeechEvent]=[]
    XCTAssertTrue(a.enqueue(t,text:"Generic fixture."){events.append($0)});XCTAssertEqual(d.starts,0);q.drain();XCTAssertEqual(d.starts,1)
    d.receive(d.id,.started);d.receive(d.id,.finished);q.drain();XCTAssertEqual(events,[.started,.finished]);a.close();q.drain();XCTAssertEqual(d.closes,1)
  }
  func testCancelDropsQueuedAndLateCallbacks(){let d=Driver(),q=Queue(),a=ready(d,q),t=token();var events:[OfflineSpeechEvent]=[]
    XCTAssertTrue(a.enqueue(t,text:"Generic fixture."){events.append($0)});a.cancel();q.drain();XCTAssertEqual(d.starts,0)
    XCTAssertTrue(a.enqueue(t,text:"Generic fixture."){events.append($0)});q.drain();a.cancel();d.receive(d.id,.finished);q.drain();XCTAssertTrue(events.isEmpty)
  }
  func testMissingNetworkAndUnknownVoiceCannotSubstitute(){let d=Driver(),q=Queue(),a=IOSOfflineSpeech(backend:d,allowed:{_ in true},schedule:q.schedule)
    for v in [[],[OfflineVoice(id:"cloud",language:"en-US",installed:true,networkRequired:true)],[OfflineVoice(id:"unknown",language:"en-US",installed:true,networkRequired:nil)]]{
      d.values=v;a.refresh{XCTAssertFalse($0)};q.drain();XCTAssertFalse(a.enqueue(token(),text:"Generic fixture."){_ in})
    };XCTAssertEqual(d.starts,0)
  }
  func testBoundsFailureAndCloseAreTruthful(){let d=Driver(),q=Queue(),a=ready(d,q),t=token();XCTAssertFalse(a.enqueue(t,text:" "){_ in});XCTAssertFalse(a.enqueue(t,text:String(repeating:"x",count:4097)){_ in});XCTAssertFalse(a.enqueue(t,text:"Generic fixture.",gain:.nan){_ in})
    d.accepted=false;var events:[OfflineSpeechEvent]=[];XCTAssertTrue(a.enqueue(t,text:"Generic fixture."){events.append($0)});q.drain();XCTAssertEqual(events,[.failed]);a.close();a.close();q.drain();XCTAssertEqual(d.closes,1)
    var done=false;a.refresh{XCTAssertFalse($0);done=true};XCTAssertTrue(done)
  }
}
