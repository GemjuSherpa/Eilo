import Foundation
import AVFoundation
import CryptoKit

// Evaluator-only: real SDK callbacks with volume zero; no audible output.
final class MutedClauseSink:NativeClauseSink {
  let speech:IOSOfflineSpeech
  init(_ speech:IOSOfflineSpeech){self.speech=speech}
  func enqueue(_ token:GenerationToken,text:String,event:@escaping(OfflineSpeechEvent)->Void)->Bool {
    speech.enqueue(token,text:text,gain:0,event:event)
  }
  func cancel(){speech.cancel()}
}

@main struct FrameworkCaptureEvaluation {
  final class Effects:ControllerEffects {
    func startCapture()->Bool{true};func playClause(_ clause:String)throws{throw LlmFailure.unavailable}
    func cancelWork(){};func releaseCapture(){};func clearVolatileContext(){}
  }
  struct Permission:MicrophonePermissionAdapter {
    func status()->MicrophonePermission{.granted}
    func request(_ complete:@escaping(MicrophonePermission)->Void){complete(.granted)}
  }
  struct Models:ModelReadinessAdapter{func status()->ModelStatus{.ready}}
  static func check(_ value:Bool,line:UInt=#line)throws{if !value{fputs("joined capture assertion \(line)\n",stderr);throw LlmFailure.unavailable}}
  static func pump(until predicate:()->Bool,seconds:Double)throws {
    let deadline=ProcessInfo.processInfo.systemUptime+seconds
    while !predicate(),ProcessInfo.processInfo.systemUptime<deadline{_ = RunLoop.main.run(mode:.default,before:Date(timeIntervalSinceNow:0.02))}
    try check(predicate())
  }
  static func run()throws {
    try check(CommandLine.arguments.count==3)
    let rows=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[1]))) as! [[String:Any]]
    let runtime="8345f333951c661d166b00e6f9362e553768f292",evidence=String(repeating:"c",count:64),key=P256.Signing.PrivateKey()
    let root=FileManager.default.temporaryDirectory.appendingPathComponent("eilo-capture-reply-"+UUID().uuidString)
    defer{try? FileManager.default.removeItem(at:root)}
    let pins=try rows.filter{$0["id"] as? String != "llm"}.map{try SpeechArtifactPin(id:$0["id"] as! String,
      filename:$0["filename"] as! String,sha256:$0["sha256"] as! String,bytes:($0["bytes"] as! NSNumber).int64Value,licenseEvidence:evidence)}
    let store=PackStore(root:root,trust:["lab-key":key.publicKey.derRepresentation],runtime:runtime,licenseEvidence:[evidence])
    let artifacts=rows.map{r->[String:Any] in let id=r["id"] as! String,name=r["filename"] as! String
      return ["id":id,"filename":name,"role":id=="llm" ? "llm":id=="vad" ? "vad":name=="tokenizer.bin" ? "tokenizer":"asr",
              "url":"https://models.example.test/"+name,"sha256":r["sha256"]!,"bytes":r["bytes"]!,
              "license":id=="llm" ? "Apache-2.0":"MIT","licenseEvidence":evidence]}
    let data=try JSONSerialization.data(withJSONObject:["schema":1,"packId":"lab-joined","revision":1,"runtimeRevision":runtime,
      "minAndroid":35,"minIos":18,"artifacts":artifacts],options:[.sortedKeys,.withoutEscapingSlashes])
    let pack=try VerifiedPack.verify(payload:data,signature:key.signature(for:data).derRepresentation,keyID:"lab-key",algorithm:"ES256",trust:["lab-key":key.publicKey.derRepresentation],runtime:runtime)
    try store.activate(pack,proofs:rows.indices.map{try VerifiedArtifact.verify(pack,index:$0,file:URL(fileURLWithPath:rows[$0]["source"] as! String))},cancel:PackCancellation())
    let vad=try SpeechPackSelection(packID:"lab-joined",runtimeRevision:runtime,kind:.vad,pins:pins.filter{$0.id=="vad"})
    let asr=try SpeechPackSelection(packID:"lab-joined",runtimeRevision:runtime,kind:.asr,pins:pins.filter{$0.id != "vad"})
    let llm=rows.last!,selection=try LlmPackSelection(packID:"lab-joined",runtimeRevision:runtime,
      model:LlmArtifactPin(id:"llm",sha256:llm["sha256"] as! String,bytes:(llm["bytes"] as! NSNumber).int64Value,licenseEvidence:evidence))
    let raw=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2]))
    try check(raw.count==37228*4)
    var input=raw.withUnsafeBytes{b in stride(from:0,to:raw.count,by:4).map{Float(bitPattern:UInt32(littleEndian:b.loadUnaligned(fromByteOffset:$0,as:UInt32.self)))}}
    defer{input.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
    try check(input.allSatisfy{$0.isFinite && (-1...1).contains($0)})
    let effects=Effects(),c=NativeController(effects:effects,permission:Permission(),models:Models())
    try check(c.dispatch(.start));try check(c.dispatch(.speechDetected,token:c.token))
    let plain=try IOSSystemSpeech(),voices=plain.voices();try check(!OfflineVoiceRegistry().refresh(voices));plain.shutdown()
    guard let voice=voices.first else{throw LlmFailure.unavailable}
    let backend=try IOSSystemSpeech(evidence:[IOSOfflineVoiceEvidence(voiceID:voice.id,osBuild:ProcessInfo.processInfo.operatingSystemVersionString)])
    let speech=IOSOfflineSpeech(backend:backend,allowed:{!$0.cancelled});defer{speech.close();c.stop()}
    var ready:Bool?;speech.refresh(requested:voice.id){ready=$0};try pump(until:{ready != nil},seconds:10);try check(ready==true)
    let worker=DispatchQueue(label:"eilo.joined.capture.inference"),specific=DispatchSpecificKey<Bool>();worker.setSpecific(key:specific,value:true)
    let vb=NativeVadAPI.linked,ab=NativeAsrAPI.linked
    let va=NativeVadAPI(create:{p in precondition(DispatchQueue.getSpecific(key:specific)==true);return vb.create(p)},
      process:{h,p,f in precondition(DispatchQueue.getSpecific(key:specific)==true);return vb.process(h,p,f)},
      destroy:{h in precondition(DispatchQueue.getSpecific(key:specific)==true);vb.destroy(h)})
    let aa=NativeAsrAPI(create:{p in precondition(DispatchQueue.getSpecific(key:specific)==true);return ab.create(p)},
      accept:{h,p in precondition(DispatchQueue.getSpecific(key:specific)==true);return ab.accept(h,p)},
      text:{h,f,b in precondition(DispatchQueue.getSpecific(key:specific)==true);return ab.text(h,f,b)},
      destroy:{h in precondition(DispatchQueue.getSpecific(key:specific)==true);ab.destroy(h)})
    var results=[[String:Any]]()
    for phase in ["speech16","followup48","quiet"] {
      let token=c.token!,rate=phase=="followup48" ? 48000:16000,slot=VadCaptureSlot(sampleRate:rate)
      defer{slot.close();worker.sync{}}
      var final:AsrText?,metadata=0,outcome:VadCaptureOutcome?
      let ticket=slot.prepare(capture:effects,controller:c,token:token)!
      let installed=worker.sync{SpeechCaptureInstaller.install(ticket:ticket,vadStore:store,vadSelection:vad,asrStore:store,asrSelection:asr,
        schedule:{worker.async(execute:$0)},vadAPI:va,asrAPI:aa,accepted:{metadata+=1;outcome=$0},recognized:{final=$0})}
      try check(installed)
      var pcm=phase=="quiet" ? [Float](repeating:0,count:80000):input+[Float](repeating:0,count:32000)
      if rate==48000{pcm=pcm.flatMap{[$0,$0,$0]}}
      defer{pcm.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
      for offset in stride(from:0,to:pcm.count,by:rate==48000 ? 960:320){
        pcm.withUnsafeBufferPointer{slot.submit(UnsafeBufferPointer(rebasing:$0[offset..<min(offset+(rate==48000 ? 960:320),pcm.count)]),sampleRate:rate)}
        worker.sync{}
      }
      slot.finish();worker.sync{};try check(metadata==1)
      var submitted=false,completed=false,digest="",starts=0
      if let final {
        digest=SHA256.hash(data:Data(final.text.utf8)).map{String(format:"%02x",$0)}.joined()
        let local=GenericSpokenTurn.localReply(controller:c,store:store,selection:selection)
        let turn=GenericSpokenTurn(controller:c,token:token,sink:MutedClauseSink(speech),configured:true,
          starter:{t,r,consume,finish in starts+=1;return local(t,r,consume,finish)})
        submitted=turn.submit(final,confidence:0.95);try check(submitted && !turn.submit(final,confidence:0.95))
        try pump(until:{c.state == .standby || c.state == .error || c.state == .stopped},seconds:180)
        try check(c.state == .standby && starts==1);completed=true
        let after=c.token!,deadline=ProcessInfo.processInfo.systemUptime+0.35
        try pump(until:{ProcessInfo.processInfo.systemUptime>=deadline},seconds:1)
        try check(c.beginGenericFollowup(after) != nil)
        withExtendedLifetime(turn){}
      }else{try check(phase=="quiet" && outcome?.result == .noSpeech && c.state == .capturing)}
      results.append(["case":phase,"recognized":final == nil ? 0:1,"metadata":metadata,"normalized_samples":outcome?.totalSamples ?? 0,
        "llm_starts":starts,"reply_submitted":submitted,"completed":completed,"transcript_sha256":digest,"context_messages":c.genericContext(c.token!)?.count ?? 0,"inference_worker_verified":true])
    }
    try check(c.endConversation());c.stop();speech.close()
    try FileManager.default.removeItem(at:root)
    let report:[String:Any]=["scope":"IOS_SIMULATOR_FRAMEWORK_CAPTURE_REPLY","physical":"NOT_RUN","production":"NOT_ENABLED",
      "microphone":"NOT_USED","confidence":"SYNTHETIC_0_95","voice_evidence":"SYNTHETIC_EXACT_VOICE_OS","cases":results,
      "temporary_pack_removed":!FileManager.default.fileExists(atPath:root.path)]
    print("EILO_CAPTURE_RESULT\t"+String(decoding:try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]),as:UTF8.self))
  }
  static func main(){do{try run()}catch{fputs("Joined capture evaluation unavailable.\n",stderr);exit(1)}}
}
