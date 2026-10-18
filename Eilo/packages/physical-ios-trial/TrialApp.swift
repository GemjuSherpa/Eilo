import UIKit
import AVFoundation
import CryptoKit

/// Internal, foreground-only operator trial. No production app caller or persistent speech content.
@main final class TrialApp:UIResponder,UIApplicationDelegate,AVSpeechSynthesizerDelegate {
  var window:UIWindow?
  private let status=UILabel(),transcript=UILabel()
  private let permissionButton=UIButton(type:.system),permission=IOSMicrophonePermission()
  private let prepare=UIButton(type:.system),probe=UIButton(type:.system),heard=UIButton(type:.system)
  private let microphone=UIButton(type:.system),model=UIButton(type:.system),stopButton=UIButton(type:.system)
  private let synth=AVSpeechSynthesizer(),eligibility=IOSCaptureEligibility(),effects=IOSCaptureEffects()
  private let installer=DispatchQueue(label:"eilo.physical.trial.prepare")
  private var store:PackStore?,vad:SpeechPackSelection?,asr:SpeechPackSelection?,llm:LlmPackSelection?
  private let audioEpoch=TrialEpoch(),modelEpoch=TrialEpoch()
  private var modelCancel:PackCancellation?,probeUtterance:AVSpeechUtterance?
  private var operatorAttested=false
  private var ready=false,probeDone=false,audible=false,synthetic=false,active=false,attached=false
  private var selectedVoice:AVSpeechSynthesisVoice?,speech:IOSOfflineSpeech?,turn:GenericSpokenTurn?,timer:Timer?
  private var controller:NativeController!,micController:NativeController!,modelController:NativeController!
  private var report:[String:Any]=["schema_version":1,"scope":"INTERNAL_IOS_FOREGROUND_TRIAL","physical_gate_acceptance":"NOT_RUN",
    "production":"NOT_ENABLED","raw_audio_saved":false,"raw_text_exported":false,"confidence":"UNAVAILABLE",
    "airplane_mode":"NOT_PROVIDED","wifi_bluetooth":"NOT_PROVIDED","sdk_probe_completed":false,
    "operator_heard_probe":false,"microphone_finals":0,"clarification_completed":0,"synthetic_model_completed":0,"synthetic_model_starts":0]
  final class NoCapture:ControllerEffects {
    func startCapture()->Bool{true};func playClause(_ clause:String)throws{throw LlmFailure.unavailable}
    func releaseCapture(){};func cancelWork(){};func clearVolatileContext(){}
  }
  final class QuietSink:NativeClauseSink {
    let speech:IOSOfflineSpeech
    init(_ speech:IOSOfflineSpeech){self.speech=speech}
    func enqueue(_ token:GenerationToken,text:String,event:@escaping(OfflineSpeechEvent)->Void)->Bool{speech.enqueue(token,text:text,gain:0.4,event:event)}
    func cancel(){speech.cancel()}
  }
  struct Readiness:ModelReadinessAdapter{let available:()->Bool;func status()->ModelStatus{available() ? .ready:.missing}}
  func application(_ application:UIApplication,didFinishLaunchingWithOptions options:[UIApplication.LaunchOptionsKey:Any]?)->Bool{true}
  func application(_ application:UIApplication,configurationForConnecting session:UISceneSession,options:UIScene.ConnectionOptions)->UISceneConfiguration{let config=UISceneConfiguration(name:"Trial",sessionRole:session.role);config.delegateClass=TrialScene.self;return config}
  func configureScene(_ scene:UIWindowScene){
    let app=UIApplication.shared
    let configURL=Bundle.main.bundleURL.appendingPathComponent("TrialAssets/operator.json")
    if let data=try? Data(contentsOf:configURL),let config=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any],
       config["schema_version"] as? Int==1,config["radio_off_attested"] as? Bool==true,config["source"] as? String=="HUMAN_OPERATOR" {
      operatorAttested=true;report["airplane_mode"]="OPERATOR_DECLARED_AT_BUILD";report["wifi_bluetooth"]="OPERATOR_DECLARED_OFF_AT_BUILD"
      report["radio_attestation_recorded_utc"]=config["recorded_utc"] as? String
    }
    let vc=UIViewController();vc.view.backgroundColor = .systemBackground
    let title=UILabel();title.text="Eilo — internal foreground trial";title.font = .preferredFont(forTextStyle:.title2);title.numberOfLines=0
    let note=UILabel();note.text="Keep Airplane Mode on, Wi-Fi/Bluetooth off and this screen open. No recordings or transcripts are exported. This does not accept physical performance or security gates.";note.numberOfLines=0;note.font = .preferredFont(forTextStyle:.footnote)
    status.numberOfLines=0;transcript.numberOfLines=0;status.text="No microphone is active. Prepare the verified lab models first."
    let stack=UIStackView(arrangedSubviews:[title,note,status,transcript,permissionButton,prepare,probe,heard,microphone,model,stopButton]);stack.axis = .vertical;stack.spacing=12;stack.translatesAutoresizingMaskIntoConstraints=false
    vc.view.addSubview(stack);NSLayoutConstraint.activate([stack.leadingAnchor.constraint(equalTo:vc.view.safeAreaLayoutGuide.leadingAnchor,constant:20),stack.trailingAnchor.constraint(equalTo:vc.view.safeAreaLayoutGuide.trailingAnchor,constant:-20),stack.topAnchor.constraint(equalTo:vc.view.safeAreaLayoutGuide.topAnchor,constant:16)])
    button(permissionButton,"Grant microphone permission (no capture)",#selector(grantPermission));button(prepare,"1. Prepare models",#selector(prepareModels));button(probe,"2. Play offline voice probe",#selector(playProbe));button(heard,"3. I heard the complete probe",#selector(confirmHeard));button(microphone,"4. Check microphone → clarification",#selector(startMic));button(model,"5. Speak fixed synthetic model reply",#selector(startModel));button(stopButton,"Stop and clear",#selector(stop))
    synth.delegate=self
    let readiness=Readiness(available:{[weak self] in self?.ready==true})
    micController=NativeController(effects:effects,permission:permission,models:readiness)
    modelController=NativeController(effects:NoCapture(),permission:permission,models:readiness);controller=micController
    effects.eligible={[weak self] in guard let self else{return false};return self.eligibility.allowed && IOSMicrophonePermission().status() == .granted}
    window=UIWindow(windowScene:scene);window?.rootViewController=vc;window?.makeKeyAndVisible()
    eligibility.visible=true;eligibility.protectedData(app.isProtectedDataAvailable)
    report["os_build"]=ProcessInfo.processInfo.operatingSystemVersionString;report["physical_memory_bytes"]=ProcessInfo.processInfo.physicalMemory
    report["phase"]="LAUNCHED_NO_CAPTURE";save();updateButtons()
    NotificationCenter.default.addObserver(forName:AVAudioSession.interruptionNotification,object:nil,queue:.main){[weak self]_ in self?.invalidateAudio()}
    NotificationCenter.default.addObserver(forName:AVAudioSession.routeChangeNotification,object:nil,queue:.main){[weak self] n in
      guard let reason=n.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,[AVAudioSession.RouteChangeReason.oldDeviceUnavailable.rawValue,AVAudioSession.RouteChangeReason.noSuitableRouteForCategory.rawValue,AVAudioSession.RouteChangeReason.override.rawValue].contains(reason) else{return};self?.invalidateAudio()
    }
  }
  private func button(_ b:UIButton,_ title:String,_ action:Selector){b.setTitle(title,for:.normal);b.titleLabel?.font = .preferredFont(forTextStyle:.headline);b.addTarget(self,action:action,for:.touchUpInside)}
  private func updateButtons(){prepare.isEnabled = !ready && !active;probe.isEnabled=ready && operatorAttested && !active;heard.isEnabled=probeDone && !audible && !active;microphone.isEnabled=ready && audible && !active;model.isEnabled=ready && audible && !active;stopButton.isEnabled=true}
  private func save(){
    // Exact owned-app aggregate file; never raw speech, prompt, transcript or model reply.
    let dir=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0]
    report["updated_utc"]=ISO8601DateFormatter().string(from:Date())
    if let bytes=try? JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]){try? bytes.write(to:dir.appendingPathComponent("trial-results.json"),options:.atomic)}
  }
  private func fail(_ code:String){stop();report["phase"]=code;status.text="Trial stopped: "+code;save()}
  @objc private func grantPermission(){permission.request{[weak self] _ in DispatchQueue.main.async{guard let self else{return};self.status.text="Permission request finished. No microphone was started.";self.report["microphone_permission_granted"]=self.permission.status() == .granted;self.save()}}}
  @objc private func prepareModels(){
    let preparation=modelEpoch.begin(),cancel=PackCancellation();modelCancel=cancel
    prepare.isEnabled=false;status.text="Verifying and preparing the local lab pack…";report["phase"]="PREPARING_MODELS";save()
    installer.async{[weak self] in
      guard let self else{return}
      var preparationStage="READ_BUNDLED_PINS"
      do {
        let assets=Bundle.main.bundleURL.appendingPathComponent("TrialAssets",isDirectory:true)
        let rows=try JSONSerialization.jsonObject(with:Data(contentsOf:assets.appendingPathComponent("pins.json"))) as! [[String:Any]]
        let runtime="8345f333951c661d166b00e6f9362e553768f292",evidence=String(repeating:"c",count:64),key=P256.Signing.PrivateKey()
        let root=FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask)[0].appendingPathComponent("internal-trial-pack",isDirectory:true)
        try? FileManager.default.removeItem(at:root)
        let store=PackStore(root:root,trust:["lab-key":key.publicKey.derRepresentation],runtime:runtime,licenseEvidence:[evidence])
        let artifacts=rows.map{r->[String:Any] in let id=r["id"] as! String,name=r["filename"] as! String
          return ["id":id,"filename":name,"role":id=="llm" ? "llm":id=="vad" ? "vad":name=="tokenizer.bin" ? "tokenizer":"asr",
            "url":"https://models.example.test/"+name,"sha256":r["sha256"]!,"bytes":r["bytes"]!,"license":id=="llm" ? "Apache-2.0":"MIT","licenseEvidence":evidence]}
        let data=try JSONSerialization.data(withJSONObject:["schema":1,"packId":"physical-lab","revision":1,"runtimeRevision":runtime,"minAndroid":35,"minIos":18,"artifacts":artifacts],options:[.sortedKeys,.withoutEscapingSlashes])
        preparationStage="VERIFY_LAB_MANIFEST"
        let pack=try VerifiedPack.verify(payload:data,signature:key.signature(for:data).derRepresentation,keyID:"lab-key",algorithm:"ES256",trust:["lab-key":key.publicKey.derRepresentation],runtime:runtime)
        preparationStage="VERIFY_BUNDLED_ARTIFACTS"
        let proofs=try rows.indices.map{try VerifiedArtifact.verify(pack,index:$0,file:assets.appendingPathComponent(rows[$0]["filename"] as! String),cancel:cancel)}
        preparationStage="ACTIVATE_LAB_PACK"
        try store.activate(pack,proofs:proofs,cancel:cancel)
        preparationStage="PROTECT_LAB_PACK"
        var protected=root;var values=URLResourceValues();values.isExcludedFromBackup=true;try protected.setResourceValues(values)
        try FileManager.default.setAttributes([.protectionKey:FileProtectionType.completeUntilFirstUserAuthentication],ofItemAtPath:root.path)
        preparationStage="SELECT_RUNTIME_PINS"
        let pins=try rows.filter{$0["id"] as? String != "llm"}.map{try SpeechArtifactPin(id:$0["id"] as! String,filename:$0["filename"] as! String,sha256:$0["sha256"] as! String,bytes:($0["bytes"] as! NSNumber).int64Value,licenseEvidence:evidence)}
        let v=try SpeechPackSelection(packID:"physical-lab",runtimeRevision:runtime,kind:.vad,pins:pins.filter{$0.id=="vad"})
        let a=try SpeechPackSelection(packID:"physical-lab",runtimeRevision:runtime,kind:.asr,pins:pins.filter{$0.id != "vad"})
        let last=rows.last!;let l=try LlmPackSelection(packID:"physical-lab",runtimeRevision:runtime,model:LlmArtifactPin(id:"llm",sha256:last["sha256"] as! String,bytes:(last["bytes"] as! NSNumber).int64Value,licenseEvidence:evidence))
        DispatchQueue.main.async{guard self.modelEpoch.current(preparation) else{return};self.modelCancel=nil;self.store=store;self.vad=v;self.asr=a;self.llm=l;self.ready=true;self.status.text="Models verified. Play the voice probe next.";self.report["phase"]="MODELS_READY";self.save();self.updateButtons()}
      }catch{let failedStage=preparationStage;DispatchQueue.main.async{guard self.modelEpoch.current(preparation) else{return};self.modelCancel=nil;self.report["preparation_stage"]=failedStage;self.fail("MODEL_PREPARATION_FAILED");self.status.text="Trial stopped: MODEL_PREPARATION_FAILED / "+failedStage}}
    }
  }
  @objc private func playProbe(){
    guard ready,operatorAttested,!active else{return};probeDone=false;audible=false
    let candidates=AVSpeechSynthesisVoice.speechVoices().filter{voice in voice.language.lowercased().hasPrefix("en") && !voice.voiceTraits.contains(.isPersonalVoice)}
    guard let voice=candidates.first(where:{$0.identifier=="com.apple.voice.compact.en-US.Samantha"}) ?? candidates.first(where:{$0.quality == .default}) else{fail("NO_INSTALLED_ENGLISH_VOICE");return}
    selectedVoice=voice;active=true;updateButtons()
    do{try AVAudioSession.sharedInstance().setCategory(.playback,mode:.default);try AVAudioSession.sharedInstance().setActive(true)}catch{fail("VOICE_SESSION_FAILED");return}
    let u=AVSpeechUtterance(string:"This is a local Eilo foreground voice test.");u.voice=voice;u.volume=0.4;probeUtterance=u;synth.speak(u)
    status.text="Listen for the complete test phrase.";report["probe_route"]=AVAudioSession.sharedInstance().currentRoute.outputs.map{$0.portType.rawValue};report["voice_id"]=voice.identifier;report["phase"]="VOICE_PROBE_PLAYING";save()
  }
  func speechSynthesizer(_ synthesizer:AVSpeechSynthesizer,didFinish utterance:AVSpeechUtterance){guard utterance===probeUtterance,eligibility.allowed else{return};probeUtterance=nil;active=false;probeDone=true;report["sdk_probe_completed"]=true;report["phase"]="VOICE_PROBE_SDK_COMPLETED";status.text="If you heard the complete phrase, tap confirmation. SDK completion alone does not prove hearing.";save();updateButtons()}
  func speechSynthesizer(_ synthesizer:AVSpeechSynthesizer,didCancel utterance:AVSpeechUtterance){guard utterance===probeUtterance else{return};probeUtterance=nil;active=false;updateButtons()}
  @objc private func confirmHeard(){guard probeDone,!active else{return};audible=true;report["operator_heard_probe"]=true;report["phase"]="SINGLE_PHRASE_OPERATOR_CONFIRMED";status.text="Single-phrase voice check confirmed. This is not a voice-quality or egress audit.";save();updateButtons()}
  @objc private func startMic(){begin(synthetic:false)}
  @objc private func startModel(){begin(synthetic:true)}
  private func begin(synthetic:Bool){
    guard ready,operatorAttested,audible,!active,let voice=selectedVoice else{return}
    let operation=audioEpoch.begin()
    controller=synthetic ? modelController:micController
    self.synthetic=synthetic;active=true;attached=false;transcript.text=nil;updateButtons()
    do {
      let backend=try IOSSystemSpeech(evidence:[IOSOfflineVoiceEvidence(voiceID:voice.identifier,osBuild:ProcessInfo.processInfo.operatingSystemVersionString)])
      let speech=IOSOfflineSpeech(backend:backend,allowed:{!$0.cancelled});self.speech=speech
      speech.refresh(requested:voice.identifier){[weak self] okay in DispatchQueue.main.async{guard let self,self.audioEpoch.current(operation) else{return};if !okay{self.fail("VOICE_READINESS_FAILED");return};self.startCapture(operation)}}
    }catch{fail("VOICE_SETUP_FAILED")}
  }
  private func startCapture(_ operation:UUID){
    guard audioEpoch.current(operation) else{return}
    guard active,eligibility.allowed else{fail("FOREGROUND_REQUIRED");return}
    guard controller.dispatch(.start) else{fail("CAPTURE_START_DENIED");return}
    status.text="Allow microphone access if prompted. Wait for Speak now.";report["phase"]="CAPTURE_START_REQUESTED";save()
    timer?.invalidate();let deadline=ProcessInfo.processInfo.systemUptime+45
    timer=Timer.scheduledTimer(withTimeInterval:0.1,repeats:true){[weak self]_ in
      guard let self,self.active,self.audioEpoch.current(operation) else{return}
      if self.controller.state == .error || (self.controller.state == .stopped && !self.controller.captureIsPending){self.fail("CAPTURE_OR_REPLY_FAILED");return}
      if !self.attached,self.controller.state == .standby{self.attach(operation)}
      if self.attached,self.controller.state == .standby{
        let key=self.synthetic ? "synthetic_model_completed":"clarification_completed";self.report[key]=(self.report[key] as? Int ?? 0)+1
        self.stop();self.report["phase"]="SINGLE_TURN_SDK_COMPLETED";self.status.text="Turn completed at the SDK boundary. No acoustic timing or hearing score is inferred.";self.save()
      }else if ProcessInfo.processInfo.systemUptime>deadline{self.fail("TRIAL_TIMEOUT")}
    }
  }
  private func attach(_ operation:UUID){
    guard audioEpoch.current(operation) else{return}
    attached=true;guard controller.dispatch(.speechDetected,token:controller.token),let token=controller.token else{fail("CAPTURE_TRANSITION_DENIED");return}
    report["microphone_permission_granted"]=permission.status() == .granted
    let session=AVAudioSession.sharedInstance();report["route_input"]=session.currentRoute.inputs.map{$0.portType.rawValue};report["route_output"]=session.currentRoute.outputs.map{$0.portType.rawValue};report["source_rate"]=session.sampleRate
    if synthetic{submit(AsrText(text:"Name one colour.",final:true),token:token,confidence:1);return}
    guard let store,let vad,let asr else{fail("MODEL_CONFIGURATION_MISSING");return}
    effects.connectSpeech(vadStore:store,vadSelection:vad,asrStore:store,asrSelection:asr,token:token,controller:controller,
      accepted:{[weak self] result in DispatchQueue.main.async{guard let self,self.active,self.audioEpoch.current(operation) else{return};self.report["normalized_samples"]=result.totalSamples;self.save();if result.result == .noSpeech{self.fail("NO_SPEECH")}}},
      recognized:{[weak self] text in DispatchQueue.main.async{guard let self,self.active,self.audioEpoch.current(operation),self.controller.recognitionAllowed(token) else{return};try? self.effects.releaseCapture();self.report["microphone_finals"]=(self.report["microphone_finals"] as? Int ?? 0)+1;self.transcript.text="Recognized (phone only): "+text.text;self.submit(text,token:token,confidence:nil)}},
      completion:{[weak self] okay in DispatchQueue.main.async{guard let self,self.active,self.audioEpoch.current(operation) else{return};if !okay{self.fail("SIGNED_CAPTURE_ATTACHMENT_FAILED");return};self.status.text="Speak now: say a short nonpersonal sentence. Unknown recognition confidence will ask for clarification.";self.report["phase"]="MICROPHONE_SPEAK_NOW";self.save()}})
  }
  private func submit(_ final:AsrText,token:GenerationToken,confidence:Float?){
    guard let speech,let store,let llm,controller.recognitionAllowed(token) else{fail("STALE_REPLY_DENIED");return}
    do{try AVAudioSession.sharedInstance().setCategory(.playback,mode:.default);try AVAudioSession.sharedInstance().setActive(true)}catch{fail("REPLY_AUDIO_SESSION_FAILED");return}
    report["speech_route"]=AVAudioSession.sharedInstance().currentRoute.outputs.map{$0.portType.rawValue}
    let local=GenericSpokenTurn.localReply(controller:controller,store:store,selection:llm)
    let turn=GenericSpokenTurn(controller:controller,token:token,sink:QuietSink(speech),configured:true,starter:{[weak self] t,r,consume,finish in
      guard let self,self.synthetic else{return false};self.report["synthetic_model_starts"]=(self.report["synthetic_model_starts"] as? Int ?? 0)+1
      return local(t,r,consume,finish)
    });self.turn=turn
    report["input_kind"]=synthetic ? "FIXED_SYNTHETIC_PROMPT":"PHYSICAL_MICROPHONE_UNCALIBRATED"
    guard turn.submit(final,confidence:confidence) else{fail("REPLY_SUBMIT_FAILED");return};report["phase"]="REPLY_SUBMITTED";save()
  }
  @objc private func stop(){audioEpoch.cancel();modelEpoch.cancel();modelCancel?.cancel();modelCancel=nil;probeUtterance=nil;timer?.invalidate();timer=nil;_ = micController?.stop();_ = modelController?.stop();speech?.close();speech=nil;turn=nil;_ = synth.stopSpeaking(at:.immediate);active=false;attached=false;transcript.text=nil;do{try AVAudioSession.sharedInstance().setActive(false,options:.notifyOthersOnDeactivation);report["audio_session_deactivated"]=true}catch{report["audio_session_deactivated"]=false};report["phase"]="STOPPED_CONTENT_CLEARED";save();updateButtons()}
  private func invalidateAudio(){stop();audible=false;probeDone=false;updateButtons()}
  func applicationWillResignActive(_ application:UIApplication){eligibility.visible=false;report["foreground"]=false;invalidateAudio()}
  func applicationDidBecomeActive(_ application:UIApplication){eligibility.visible=true;eligibility.protectedData(application.isProtectedDataAvailable);controller.permissionChanged();report["foreground"]=true;save()}
  func applicationProtectedDataWillBecomeUnavailable(_ application:UIApplication){eligibility.protectedData(false);invalidateAudio();_ = controller.privacyTransition(.lock)}
  func applicationProtectedDataDidBecomeAvailable(_ application:UIApplication){eligibility.protectedData(true);_ = controller.privacyTransition(.unlock)}
}

final class TrialScene:UIResponder,UIWindowSceneDelegate {
  func scene(_ scene:UIScene,willConnectTo session:UISceneSession,options:UIScene.ConnectionOptions){guard let windowScene=scene as? UIWindowScene else{return};(UIApplication.shared.delegate as? TrialApp)?.configureScene(windowScene)}
  func sceneWillResignActive(_ scene:UIScene){(UIApplication.shared.delegate as? TrialApp)?.applicationWillResignActive(UIApplication.shared)}
  func sceneDidBecomeActive(_ scene:UIScene){(UIApplication.shared.delegate as? TrialApp)?.applicationDidBecomeActive(UIApplication.shared)}
  func sceneDidDisconnect(_ scene:UIScene){(UIApplication.shared.delegate as? TrialApp)?.applicationWillResignActive(UIApplication.shared)}
}
