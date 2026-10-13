import Foundation
import AVFoundation

@main struct OfflineSpeechProbe {
  final class Effects:ControllerEffects{func startCapture()->Bool{true};func playClause(_ clause:String){};func cancelWork(){};func releaseCapture(){};func clearVolatileContext(){}}
  struct Permission:MicrophonePermissionAdapter{func status()->MicrophonePermission{.granted};func request(_ completion:@escaping(MicrophonePermission)->Void){completion(.granted)}}
  struct Models:ModelReadinessAdapter{func status()->ModelStatus{.ready}}
  static func run()throws {
    let plain=try IOSSystemSpeech();let observed=plain.voices();let missing=OfflineVoiceRegistry()
    guard !missing.refresh(observed) else{throw OfflineSpeechFailure.unavailable};plain.shutdown()
    var report:[String:Any]=["task":"VC-VOICE-03","platform":"iOS27 ARM64 iPhone 18 Pro simulator","microphone":"NOT USED",
      "default_unknown_offline_gate":"PASS","physical_airplane_mode_and_traffic":"NOT RUN","offline_evidence":"Synthetic exact-voice/OS test record only; no production approval"]
    if let voice=observed.first {
      let proof=IOSOfflineVoiceEvidence(voiceID:voice.id,osBuild:ProcessInfo.processInfo.operatingSystemVersionString)
      let backend=try IOSSystemSpeech(evidence:[proof]);let speech=IOSOfflineSpeech(backend:backend,allowed:{!$0.cancelled})
      var prepared:Bool?;speech.refresh(requested:voice.id){prepared=$0}
      let deadline=ProcessInfo.processInfo.systemUptime+30
      while prepared==nil && ProcessInfo.processInfo.systemUptime<deadline{_ = RunLoop.main.run(mode:.default,before:Date(timeIntervalSinceNow:0.05))}
      guard prepared==true else{throw OfflineSpeechFailure.unavailable}
      let c=NativeController(effects:Effects(),permission:Permission(),models:Models());guard c.dispatch(.start),let token=c.token else{throw OfflineSpeechFailure.unavailable}
      var finished:OfflineSpeechEvent?,started:Double?
      let began=ProcessInfo.processInfo.systemUptime
      guard speech.enqueue(token,text:"This is a generic offline speech test.",event:{event in
        if event == .started{started=ProcessInfo.processInfo.systemUptime-began}else{finished=event}
      }) else{throw OfflineSpeechFailure.unavailable}
      while finished==nil && ProcessInfo.processInfo.systemUptime<deadline{_ = RunLoop.main.run(mode:.default,before:Date(timeIntervalSinceNow:0.05))}
      guard finished == .finished else{speech.close();throw OfflineSpeechFailure.unavailable}
      c.stop();speech.cancel();speech.close();_ = RunLoop.main.run(mode:.default,before:Date(timeIntervalSinceNow:0.1))
      report["SDK_synthesis_completion"]="PASS";report["SDK_start_callback_seconds"]=started ?? -1
      report["first_audible_audio_seconds"]="NOT MEASURED; SDK start is not audible playback evidence"
    }else{report["SDK_synthesis_completion"]="NOT RUN; no observed English voice"}
    let data=try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys])
    print("EILO_SPEECH_RESULT\t"+String(decoding:data,as:UTF8.self))
  }
  static func main(){do{try run()}catch{fputs("Offline speech probe unavailable\n",stderr);exit(1)}}
}
