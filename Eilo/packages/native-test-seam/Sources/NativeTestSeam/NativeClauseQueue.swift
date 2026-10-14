import Foundation

final class SpeechWorkTicket {
  weak var controller:NativeController?
  let token:GenerationToken,cancel:()->Void
  var cancelled=false // Controller monitor only.
  init(controller:NativeController,token:GenerationToken,cancel:@escaping()->Void){self.controller=controller;self.token=token;self.cancel=cancel}
}
/// Sink methods schedule only; no blocking SDK work or joins under the controller.
protocol NativeClauseSink:AnyObject {
  func enqueue(_ token:GenerationToken,text:String,event:@escaping(OfflineSpeechEvent)->Void)->Bool
  func cancel()
}
final class IOSClauseSink:NativeClauseSink {
  private let speech:IOSOfflineSpeech
  init(_ speech:IOSOfflineSpeech){self.speech=speech}
  func enqueue(_ token:GenerationToken,text:String,event:@escaping(OfflineSpeechEvent)->Void)->Bool{speech.enqueue(token,text:text,event:event)}
  func cancel(){speech.cancel()}
}
/// One active + four waiting natural clauses, each <=1024 UTF-8 bytes. Controller
/// transactions serialize queue mutations, Stop and callbacks. Caller retains this
/// native queue until sealed/cancelled. Authorization defaults to denied; S07 owns
/// pre-speech policy. Reference release is not certified String/SDK memory erasure.
final class NativeClauseQueue {
  private final class Clause{let id=UUID();var text:String?,timeout:(any IdleCancellation)?;init(_ text:String){self.text=text}}
  private static let timers=NativeIdleScheduler()
  private let controller:NativeController,sink:any NativeClauseSink,scheduler:any IdleScheduler,authorized:(GenerationToken,String)->Bool
  private let ledger=PlaybackLedger()
  private let completed:(GenerationToken)->Void,cleared:()->Void
  private var ticket:SpeechWorkTicket!,waiting:[Clause]=[],active:Clause?,fragment="",sealed=false,closed=false
  private init(controller:NativeController,sink:any NativeClauseSink,scheduler:any IdleScheduler,authorized:@escaping(GenerationToken,String)->Bool,completed:@escaping(GenerationToken)->Void,cleared:@escaping()->Void){self.controller=controller;self.sink=sink;self.scheduler=scheduler;self.authorized=authorized;self.completed=completed;self.cleared=cleared}
  static func create(controller:NativeController,token:GenerationToken,sink:any NativeClauseSink,scheduler:any IdleScheduler=timers,completed:@escaping(GenerationToken)->Void={_ in},cleared:@escaping()->Void={},authorized:@escaping(GenerationToken,String)->Bool={_,_ in false})->NativeClauseQueue? {
    let queue=NativeClauseQueue(controller:controller,sink:sink,scheduler:scheduler,authorized:authorized,completed:completed,cleared:cleared)
    guard let ticket=controller.prepareSpeechWork(token,cancel:{[weak queue] in queue?.clear()},publish:{queue.ticket=$0}) else{return nil}
    queue.ticket=ticket;return queue
  }
  @discardableResult func enqueue(_ text:String)->Bool{controller.speechTransaction(ticket){
    guard !closed,!sealed else{return false}
    guard !text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty,text.utf8.count<=1024,!text.contains("\0"),waiting.count<4,authorized(ticket.token,text) else{fail();return false}
    guard !closed,!ticket.cancelled,controller.accepts(ticket.token) else{return false}
    let clause=Clause(text);ledger.produced(clause.id);waiting.append(clause);pump();return !closed
  }}
  /// Decoded policy-approved fragments only; hold punctuation until whitespace.
  @discardableResult func append(_ text:String)->Bool{controller.speechTransaction(ticket){
    guard !closed,!sealed else{return false}
    guard text.utf8.count<=1024,!text.contains("\0") else{fail();return false}
    for character in text {
      if character.isWhitespace,let last=fragment.last,".!?;:".contains(last){
        let clause=fragment.trimmingCharacters(in:.whitespacesAndNewlines);fragment="";guard enqueue(clause) else{return false}
      }
      fragment.append(character);guard fragment.utf8.count<=1024 else{fail();return false}
      if character=="\n",!fragment.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty {
        let clause=fragment.trimmingCharacters(in:.whitespacesAndNewlines);fragment="";guard enqueue(clause) else{return false}
      }
    };return true
  }}
  @discardableResult func seal()->Bool{
    var accepted=false
    _ = controller.speechTransaction(ticket){
      guard !closed,!sealed else{return false}
      let clause=fragment.trimmingCharacters(in:.whitespacesAndNewlines);fragment=""
      if !clause.isEmpty,!enqueue(clause){return false}
      sealed=true;accepted=true;pump();return true
    };return accepted
  }
  private func pump(){
    guard !closed,active==nil else{return}
    if waiting.isEmpty{if sealed{closed=true;completed(ticket.token);controller.finishSpeechWork(ticket)};return}
    let clause=waiting.removeFirst();active=clause
    clause.timeout=scheduler.schedule(60_000){[weak self,weak clause] in if let clause{self?.event(clause,.failed)}}
    guard !closed,active===clause else{clause.timeout?.cancel();clause.timeout=nil;return}
    let text=clause.text;clause.text=nil
    guard let text,authorized(ticket.token,text),!closed,!ticket.cancelled,controller.accepts(ticket.token),sink.enqueue(ticket.token,text:text,event:{[weak self,clause] in self?.event(clause,$0)}) else{if active===clause{fail()};return}
  }
  private func event(_ clause:Clause,_ event:OfflineSpeechEvent){_ = controller.speechTransaction(ticket){
    guard !closed,active===clause else{return false}
    if event != .started{clause.timeout?.cancel();clause.timeout=nil}
    ledger.event(clause.id,event)
    switch event {
    case .started:return controller.speechStarted(ticket)
    case .finished:active=nil;_ = controller.speechGap(ticket);pump();return true
    default:fail();return false
    }
  }}
  private func fail(){clear();_ = controller.dispatch(.failure,failure:.unavailable,token:ticket.token)}
  private func clear(){ledger.cancel(active:active?.id,waiting:waiting.map{$0.id});if !controller.speechPrivacyCurrent(ticket){ledger.clear()};closed=true;fragment="";active?.timeout?.cancel();active?.timeout=nil;active?.text=nil;active=nil;waiting.forEach{$0.text=nil};waiting.removeAll();cleared();sink.cancel()}
  func progress(permitted:()->Bool={false})->[PlaybackProgress]{controller.speechMetadata(ticket,permitted:permitted,ledger:ledger)}
  func cancel(){_ = controller.speechTransaction(ticket){controller.cancelGeneration();return true}}
}
