import Foundation
import AVFoundation
import CryptoKit
import Darwin

@main struct JoinedEvaluation {
  final class Effects:ControllerEffects{func startCapture()->Bool{true};func playClause(_ clause:String)throws{throw LlmFailure.unavailable};func cancelWork(){};func releaseCapture(){};func clearVolatileContext(){}}
  struct Permission:MicrophonePermissionAdapter{func status()->MicrophonePermission{.granted};func request(_ complete:@escaping(MicrophonePermission)->Void){complete(.granted)}}
  struct Models:ModelReadinessAdapter{func status()->ModelStatus{.ready}}
  static func signedFixture(_ root: URL) throws -> (PackStore,LlmPackSelection) {
    let key = P256.Signing.PrivateKey(), runtime = "8345f333951c661d166b00e6f9362e553768f292", evidence = String(repeating:"c",count:64)
    let hash = CommandLine.arguments[2], size = Int64(CommandLine.arguments[3]) ?? -1, trust = ["evaluation-key":key.publicKey.derRepresentation]
    let store = PackStore(root:root,trust:trust,runtime:runtime,licenseEvidence:[evidence])
    let payload = try JSONSerialization.data(withJSONObject:["schema":1,"packId":"evaluation-pack","revision":1,"runtimeRevision":runtime,
      "minAndroid":35,"minIos":18,"artifacts":[["id":"model","filename":"model.gguf","role":"llm","url":"https://models.example.test/model.gguf",
      "sha256":hash,"bytes":size,"license":"Apache-2.0","licenseEvidence":evidence]]],options:[.sortedKeys,.withoutEscapingSlashes])
    let pack = try VerifiedPack.verify(payload:payload,signature:key.signature(for:payload).derRepresentation,keyID:"evaluation-key",algorithm:"ES256",trust:trust,runtime:runtime)
    try store.activate(pack,proofs:[VerifiedArtifact.verify(pack,index:0,file:URL(fileURLWithPath:CommandLine.arguments[1]))],cancel:PackCancellation())
    return (store,try LlmPackSelection(packID:"evaluation-pack",runtimeRevision:runtime,model:LlmArtifactPin(id:"model",sha256:hash,bytes:size,licenseEvidence:evidence)))
  }
  static func check(_ value: Bool) throws {
    guard value else { throw LlmFailure.unavailable }
  }

  static func audio(_ path:String)throws->[Float]{let f=try AVAudioFile(forReading:URL(fileURLWithPath:path));try check(f.processingFormat.sampleRate==16000 && f.processingFormat.channelCount==1 && f.length<=480000);guard let b=AVAudioPCMBuffer(pcmFormat:f.processingFormat,frameCapacity:AVAudioFrameCount(f.length)) else{throw LlmFailure.unavailable};try f.read(into:b);guard let pcm=b.floatChannelData?[0] else{throw LlmFailure.unavailable};defer{pcm.update(repeating:0,count:Int(b.frameLength))};return Array(UnsafeBufferPointer(start:pcm,count:Int(b.frameLength)))}
  static func pump(until predicate:()->Bool,seconds:Double)throws{let deadline=ProcessInfo.processInfo.systemUptime+seconds;while !predicate(),ProcessInfo.processInfo.systemUptime<deadline{_ = RunLoop.main.run(mode:.default,before:Date(timeIntervalSinceNow:0.02))};try check(predicate())}
  static func run()throws {
    try check(CommandLine.arguments.count==8)
    let root=FileManager.default.temporaryDirectory.appendingPathComponent("eilo-joined-"+UUID().uuidString);defer{try? FileManager.default.removeItem(at:root)}
    let (store,selection)=try signedFixture(root)
    let c=NativeController(effects:Effects(),permission:Permission(),models:Models());try check(c.dispatch(.start));let standby=c.token!
    let dir=CommandLine.arguments[4],paths=try WakeModelPaths(encoder:dir+"/encoder-epoch-12-avg-2-chunk-16-left-64.int8.onnx",decoder:dir+"/decoder-epoch-12-avg-2-chunk-16-left-64.onnx",joiner:dir+"/joiner-epoch-12-avg-2-chunk-16-left-64.int8.onnx",tokens:dir+"/tokens.txt")
    let detector=WakeDetector(configuration:try WakeConfiguration(phrase:"HEY EILO",threshold:0.125,boost:1.5),verified:{true},open:{try NativeWakeStream(paths:paths,configuration:$0,verified:{true})});try check(detector.begin(standby))
    var wake=try audio(CommandLine.arguments[5]);defer{wake.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
    var activation:WakeActivation?
    wake.withUnsafeBufferPointer{p in for offset in stride(from:0,to:p.count,by:320){if activation==nil{activation=detector.process(standby,input:UnsafeBufferPointer(rebasing:p[offset..<min(offset+320,p.count)]),sampleRate:16000)}}}
    try check(activation?.apply(c)==true);detector.close();let capture=c.token!
    let asr=StreamingAsr(capture,allowed:{c.recognitionAllowed(capture)},open:{try NativeAsrStream(directory:CommandLine.arguments[6],verified:{!capture.cancelled})})
    var question=try audio(CommandLine.arguments[7]);defer{question.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
    try question.withUnsafeBufferPointer{p in for offset in stride(from:0,to:p.count,by:320){try check(asr.accept(UnsafeBufferPointer(rebasing:p[offset..<min(offset+320,p.count)])))}}
    guard let final=asr.poll(finish:true),!final.text.isEmpty else{throw LlmFailure.unavailable}
    let plain=try IOSSystemSpeech();let voices=plain.voices();try check(!OfflineVoiceRegistry().refresh(voices));plain.shutdown();guard let voice=voices.first else{throw LlmFailure.unavailable}
    let backend=try IOSSystemSpeech(evidence:[IOSOfflineVoiceEvidence(voiceID:voice.id,osBuild:ProcessInfo.processInfo.operatingSystemVersionString)])
    let speech=IOSOfflineSpeech(backend:backend,allowed:{!$0.cancelled});var ready:Bool?;speech.refresh(requested:voice.id){ready=$0};try pump(until:{ready != nil},seconds:10);try check(ready==true)
    let turn=GenericSpokenTurn(controller:c,token:capture,sink:IOSClauseSink(speech),configured:true,starter:GenericSpokenTurn.localReply(controller:c,store:store,selection:selection))
    try check(turn.submit(final,confidence:0.95));try pump(until:{c.state == .standby || c.state == .error || c.state == .stopped},seconds:180);try check(c.state == .standby)
    c.stop();speech.close();try FileManager.default.removeItem(at:root);try check(!FileManager.default.fileExists(atPath:root.path))
    let report:[String:Any]=["task":"VC-JOIN-01","platform":"iPhone 18 Pro ARM64 simulator","microphone":"NOT USED","history_persistence":"NONE","wake_activation":"PASS","ASR_final_once":"PASS","signed_cpu_worker":"PASS","configured_clause_policy":"PASS","SDK_speech_completion":"PASS","normal_unknown_offline_gate":"PASS","temporary_signed_pack_removed":true]
    let data=try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]);print("EILO_JOIN_RESULT\t"+String(decoding:data,as:UTF8.self))
  }
  static func main(){do{try run()}catch{fputs("Joined evaluation unavailable.\n",stderr);exit(1)}}
}
