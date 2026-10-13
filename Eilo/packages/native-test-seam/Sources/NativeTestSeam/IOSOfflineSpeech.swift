import Foundation
import AVFoundation

enum OfflineSpeechEvent { case started, finished, interrupted, failed }
enum OfflineSpeechFailure:Error{case unavailable}
struct IOSOfflineVoiceEvidence: Hashable { let voiceID, osBuild: String }
protocol IOSSpeechBackend: AnyObject {
  func voices() -> [OfflineVoice]
  func listener(_ receive: @escaping (UUID,OfflineSpeechEvent)->Void)
  func start(id:UUID,text:String,voice:OfflineVoice,rate:Float,gain:Float)->Bool
  func stop()
  func shutdown()
}
/// Main-thread SDK boundary; explicit native construction. Quality does not prove
/// offline capability. Personal voices/permission prompts and default-language fallback
/// are excluded; explicit installed voice + exact voice/OS evidence are required.
// The SDK delegate requires Sendable. Mutable SDK state is confined to main;
// callbacks arriving elsewhere are marshaled before any state is accessed.
final class IOSSystemSpeech:NSObject,IOSSpeechBackend,AVSpeechSynthesizerDelegate,@unchecked Sendable {
  private let synth:AVSpeechSynthesizer
  private let evidence:Set<IOSOfflineVoiceEvidence>
  private let build:String
  private var utterance:AVSpeechUtterance?,identifier:UUID?
  private var receive:(UUID,OfflineSpeechEvent)->Void={_,_ in}
  init(evidence:Set<IOSOfflineVoiceEvidence>=[],osBuild:String=ProcessInfo.processInfo.operatingSystemVersionString) throws {
    guard Thread.isMainThread else{throw OfflineSpeechFailure.unavailable}
    self.evidence=evidence;build=osBuild;synth=AVSpeechSynthesizer();super.init();synth.delegate=self
  }
  private func ordinary(_ voice:AVSpeechSynthesisVoice)->Bool {
    if #available(iOS 17.0,macOS 14.0,*) { if voice.voiceTraits.contains(.isPersonalVoice){return false} }
    return voice.language.lowercased().hasPrefix("en-") || voice.language.lowercased()=="en"
  }
  func voices()->[OfflineVoice] {
    guard Thread.isMainThread else{return []}
    return Array(AVSpeechSynthesisVoice.speechVoices().filter(ordinary).prefix(129)).map {
      OfflineVoice(id:$0.identifier,language:$0.language,installed:true,networkRequired:nil,
        offlineVerified:evidence.contains(IOSOfflineVoiceEvidence(voiceID:$0.identifier,osBuild:build)))
    }
  }
  func listener(_ receive:@escaping(UUID,OfflineSpeechEvent)->Void){
    if !Thread.isMainThread{DispatchQueue.main.async(execute:DispatchWorkItem{[weak self] in self?.listener(receive)});return}
    self.receive=receive
  }
  func start(id:UUID,text:String,voice:OfflineVoice,rate:Float,gain:Float)->Bool {
    guard Thread.isMainThread,utterance==nil,voices().contains(voice),voice.offlineVerified,
      let exact=AVSpeechSynthesisVoice(identifier:voice.id),ordinary(exact) else{return false}
    let item=AVSpeechUtterance(string:text);item.voice=exact;item.volume=gain
    item.rate=min(AVSpeechUtteranceMaximumSpeechRate,max(AVSpeechUtteranceMinimumSpeechRate,AVSpeechUtteranceDefaultSpeechRate*rate))
    utterance=item;identifier=id;synth.speak(item);return true
  }
  func stop(){if !Thread.isMainThread{DispatchQueue.main.async(execute:DispatchWorkItem{[weak self] in self?.stop()});return};utterance=nil;identifier=nil;_ = synth.stopSpeaking(at:.immediate)}
  func shutdown(){if !Thread.isMainThread{DispatchQueue.main.async(execute:DispatchWorkItem{[weak self] in self?.shutdown()});return};stop();synth.delegate=nil;receive={_,_ in}}
  private func event(_ item:AVSpeechUtterance,_ event:OfflineSpeechEvent){
    if !Thread.isMainThread{DispatchQueue.main.async(execute:DispatchWorkItem{[weak self,item] in self?.event(item,event)});return}
    guard item===utterance,let id=identifier else{return}
    if event != .started{utterance=nil;identifier=nil};receive(id,event)
  }
  func speechSynthesizer(_ synthesizer:AVSpeechSynthesizer,didStart item:AVSpeechUtterance){event(item,.started)}
  func speechSynthesizer(_ synthesizer:AVSpeechSynthesizer,didFinish item:AVSpeechUtterance){event(item,.finished)}
  func speechSynthesizer(_ synthesizer:AVSpeechSynthesizer,didCancel item:AVSpeechUtterance){event(item,.interrupted)}
}
/// One current clause. Main SDK dispatch is asynchronous; controller cancellation
/// clears queued references immediately and schedules SDK stop without a join.
/// Actual audio-stop timing and framework retention remain physical/privacy gates.
final class IOSOfflineSpeech {
  private final class Request {
    let id=UUID(),token:GenerationToken,voice:OfflineVoiceSelection,rate:Float,gain:Float,event:(OfflineSpeechEvent)->Void
    var text:String?
    init(token:GenerationToken,voice:OfflineVoiceSelection,text:String,rate:Float,gain:Float,event:@escaping(OfflineSpeechEvent)->Void){
      self.token=token;self.voice=voice;self.text=text;self.rate=rate;self.gain=gain;self.event=event
    }
  }
  let registry:OfflineVoiceRegistry
  private let backend:any IOSSpeechBackend,allowed:(GenerationToken)->Bool,schedule:(@escaping()->Void)->Void
  private let lock=NSLock()
  private var active:Request?,closed=false
  init(backend:any IOSSpeechBackend,registry:OfflineVoiceRegistry=OfflineVoiceRegistry(),allowed:@escaping(GenerationToken)->Bool={_ in false},
       schedule:@escaping(@escaping()->Void)->Void={DispatchQueue.main.async(execute:DispatchWorkItem(block:$0))}){
    self.backend=backend;self.registry=registry;self.allowed=allowed;self.schedule=schedule
    backend.listener{[weak self] id,event in self?.schedule{[weak self] in self?.deliver(id,event)}}
  }
  private var isClosed:Bool{lock.lock();defer{lock.unlock()};return closed}
  func refresh(requested:String?=nil,complete:@escaping(Bool)->Void){
    if isClosed{complete(false);return}
    schedule{[self] in
      lock.lock();let old=active;active=nil;old?.text=nil;lock.unlock()
      if old != nil{backend.stop()}
      complete(!isClosed && registry.refresh(backend.voices(),requested:requested))
    }
  }
  @discardableResult func enqueue(_ token:GenerationToken,text:String,rate:Float=1,gain:Float=1,event:@escaping(OfflineSpeechEvent)->Void)->Bool{
    guard !isClosed,!token.cancelled,!text.trimmingCharacters(in:.whitespacesAndNewlines).isEmpty,text.utf8.count<=4096,
      rate.isFinite,(0.5...1.5).contains(rate),gain.isFinite,(0...1).contains(gain),allowed(token),let voice=registry.selection() else{return false}
    let request=Request(token:token,voice:voice,text:text,rate:rate,gain:gain,event:event)
    lock.lock();guard active==nil,!closed else{lock.unlock();return false};active=request;lock.unlock()
    schedule{[self] in
      guard current(request) else{abandon(request);return}
      lock.lock();let clause=request.text;request.text=nil;lock.unlock();guard let clause else{return}
      if !backend.start(id:request.id,text:clause,voice:voice.voice,rate:rate,gain:gain){deliver(request.id,.failed)}
      if !current(request){abandon(request);backend.stop()}
    };return true
  }
  private func current(_ r:Request)->Bool{
    lock.lock();let attached=active===r && !closed;lock.unlock()
    return attached && !r.token.cancelled && registry.current(r.voice) && allowed(r.token)
  }
  private func abandon(_ r:Request){lock.lock();r.text=nil;if active===r{active=nil};lock.unlock()}
  private func deliver(_ id:UUID,_ event:OfflineSpeechEvent){
    lock.lock();let r=active;lock.unlock();guard let r,r.id==id else{return}
    guard current(r) else{abandon(r);return};if event != .started{abandon(r)};r.event(event)
  }
  func cancel(){lock.lock();active?.text=nil;active=nil;lock.unlock();schedule{[backend] in backend.stop()}}
  func close(){lock.lock();guard !closed else{lock.unlock();return};closed=true;active?.text=nil;active=nil;lock.unlock()
    registry.invalidate();schedule{[backend] in backend.shutdown()}
  }
}
