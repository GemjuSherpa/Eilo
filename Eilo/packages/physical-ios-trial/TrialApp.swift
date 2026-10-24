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
  private let modelQuality=UIButton(type:.system),modelQualityNote=UILabel(),modelQualityAnswer=UILabel()
  private let modelQualityRatings=(1...5).map{_ in UIButton(type:.system)}
  private let modelQualitySession=TrialModelQualitySession(),modelQualitySessionID=UUID().uuidString
  private var modelQualityCancellation:TrialModelCancellation?
  private var modelQualityRunning=false
  private let lifecycleButton=UIButton(type:.system),lifecycleNote=UILabel()
  private let lifecycle=TrialLifecycle()
  private var lifecycleUtterance:AVSpeechUtterance?,lifecycleTimer:Timer?,lifecycleOperation:UUID?
  private let lifecycleSession=UUID().uuidString
  private let residentDiagnostic=UIButton(type:.system)
  private var residentAutoRun=false,residentRunning=false,residentUsed=false
  private var residentRows=[[String:Any]](),comparisonLlm:LlmPackSelection?
  private let residentProcess=UUID().uuidString
  private let phaseDiagnostic=UIButton(type:.system)
  private var phaseAutoRun=false,phaseRunning=false,phaseUsed=false
  private var phaseRows=[[String:Any]](),batteryMonitoring:Bool?
  private let phaseProcess=UUID().uuidString
  private let modelDiagnostic=UIButton(type:.system)
  private var modelDiagnosticAutoRun=false,modelDiagnosticRunning=false,modelDiagnosticUsed=false
  private var diagnosticIdleTimer:Bool?
  private var diagnosticCancellation:TrialModelCancellation?
  private let modelDiagnosticProcess=UUID().uuidString
  private let fileAsr=UIButton(type:.system)
  private var fileAsrAutoRun=false,fileAsrRunning=false
  private let quality=UIButton(type:.system),qualityNote=UILabel(),ratings=(1...5).map{_ in UIButton(type:.system)}
  private let survey=TrialVoiceSurvey()
  private var surveyUtterance:AVSpeechUtterance?,surveyTicket:UUID?,surveyVoiceID:String?
  private var voiceFixtures:[String]=[]
  private let fixtureDigest="35eecc8aa70638999474fa9f29e94aed062ae943774fc1ed7d4188bd72dfa2b6"
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
    struct Corpus:Decodable{struct Phrase:Decodable{let id,text:String};let schema:Int,language:String,utterances:[Phrase]}
    if let data=try? Data(contentsOf:Bundle.main.bundleURL.appendingPathComponent("TrialAssets/voice-trial-fixtures.json")),
       SHA256.hash(data:data).map({String(format:"%02x",$0)}).joined()==fixtureDigest,
       let corpus=try? JSONDecoder().decode(Corpus.self,from:data),corpus.schema==1,corpus.language=="en",
       corpus.utterances.map({$0.id})==(1...12).map({String(format:"voice-%02d",$0)}){voiceFixtures=corpus.utterances.map{$0.text}}
    qualityNote.numberOfLines=0;qualityNote.text="Listening survey: 12 fixed phrases. Rate only after playback: 1 unintelligible, 5 fully clear. Timing and traffic verification remain unrun. No microphone is used."
    let scoreRow=UIStackView(arrangedSubviews:ratings);scoreRow.axis = .horizontal;scoreRow.distribution = .fillEqually
    for (i,b) in ratings.enumerated(){b.tag=i+1;button(b,String(i+1),#selector(rateQuality(_:)))}
    modelQualityNote.numberOfLines=0;modelQualityNote.text="Answer quality: six fixed prompts. Read the rubric and answer, then rate 1 incorrect/unusable to 5 correct/clear. This session's scores save automatically; leave the app open for export. No audio."
    modelQualityAnswer.numberOfLines=0
    let modelScoreRow=UIStackView(arrangedSubviews:modelQualityRatings);modelScoreRow.axis = .horizontal;modelScoreRow.distribution = .fillEqually
    for (i,b) in modelQualityRatings.enumerated(){b.tag=i+1;button(b,String(i+1),#selector(rateModelQuality(_:)))}
    button(modelQuality,"9. Review next fixed model answer",#selector(runModelQuality))
    button(modelDiagnostic,"8. Run fixed CPU model diagnostic (no audio)",#selector(runModelDiagnostic))
    button(fileAsr,"7. Run six-file ASR diagnostic (no mic)",#selector(runFileAsr))
    button(quality,"6. Play next listening-survey phrase",#selector(playQuality))
    button(phaseDiagnostic,"10. Run 18 native-phase samples (no audio)",#selector(runPhaseDiagnostic))
    phaseDiagnostic.isHidden = !TrialPhaseDiagnostic.available
    button(residentDiagnostic,"11. Run alternating resident-model comparison (no audio)",#selector(runResidentDiagnostic))
    residentDiagnostic.isHidden = !TrialResidentDiagnostic.available
    let stack=UIStackView(arrangedSubviews:[title,note,status,transcript,permissionButton,prepare,probe,heard,microphone,model,qualityNote,quality,scoreRow,fileAsr,modelDiagnostic,modelQualityNote,modelQuality,modelQualityAnswer,modelScoreRow,phaseDiagnostic,residentDiagnostic,lifecycleNote,lifecycleButton,stopButton]);stack.axis = .vertical;stack.spacing=12;stack.translatesAutoresizingMaskIntoConstraints=false
    if TrialResidentDiagnostic.available{
      let otherControls:[UIView]=[transcript,permissionButton,probe,heard,microphone,model,qualityNote,quality,scoreRow,fileAsr,modelDiagnostic,modelQualityNote,modelQuality,modelQualityAnswer,modelScoreRow,phaseDiagnostic]
      for view in otherControls{view.isHidden=true}
    }
    let scroll=UIScrollView();scroll.translatesAutoresizingMaskIntoConstraints=false;vc.view.addSubview(scroll);scroll.addSubview(stack)
    NSLayoutConstraint.activate([scroll.leadingAnchor.constraint(equalTo:vc.view.safeAreaLayoutGuide.leadingAnchor),scroll.trailingAnchor.constraint(equalTo:vc.view.safeAreaLayoutGuide.trailingAnchor),scroll.topAnchor.constraint(equalTo:vc.view.safeAreaLayoutGuide.topAnchor),scroll.bottomAnchor.constraint(equalTo:vc.view.safeAreaLayoutGuide.bottomAnchor),stack.leadingAnchor.constraint(equalTo:scroll.contentLayoutGuide.leadingAnchor,constant:20),stack.trailingAnchor.constraint(equalTo:scroll.contentLayoutGuide.trailingAnchor,constant:-20),stack.topAnchor.constraint(equalTo:scroll.contentLayoutGuide.topAnchor,constant:16),stack.bottomAnchor.constraint(equalTo:scroll.contentLayoutGuide.bottomAnchor,constant:-20),stack.widthAnchor.constraint(equalTo:scroll.frameLayoutGuide.widthAnchor,constant:-40)])
    button(permissionButton,"Grant microphone permission (no capture)",#selector(grantPermission));button(prepare,"1. Prepare models",#selector(prepareModels));button(probe,"2. Play offline voice probe",#selector(playProbe));button(heard,"3. I heard the complete probe",#selector(confirmHeard));button(microphone,"4. Check microphone → clarification",#selector(startMic));button(model,"5. Speak fixed synthetic model reply",#selector(startModel));button(stopButton,"Stop and clear",#selector(operatorStop))
    button(lifecycleButton,"12. Start next lifecycle check",#selector(startLifecycle))
    lifecycleNote.numberOfLines=0
    lifecycleNote.text="Six bounded Stop/background/lock checks. No background listening or acoustic latency acceptance."
    synth.delegate=self
    let readiness=Readiness(available:{[weak self] in self?.ready==true})
    micController=NativeController(effects:effects,permission:permission,models:readiness)
    modelController=NativeController(effects:NoCapture(),permission:permission,models:readiness);controller=micController
    effects.eligible={[weak self] in guard let self else{return false};return self.eligibility.allowed && IOSMicrophonePermission().status() == .granted}
    window=UIWindow(windowScene:scene);window?.rootViewController=vc;window?.makeKeyAndVisible()
    eligibility.visible=true;eligibility.protectedData(app.isProtectedDataAvailable)
    report["os_build"]=ProcessInfo.processInfo.operatingSystemVersionString;report["physical_memory_bytes"]=ProcessInfo.processInfo.physicalMemory
    report["phase"]="LAUNCHED_NO_CAPTURE";save();saveLifecycle();updateButtons()
    if CommandLine.arguments.contains("--run-resident-model-comparison"),TrialResidentDiagnostic.available{residentAutoRun=true;prepareModels()}
    else if CommandLine.arguments.contains("--run-native-phase-diagnostic"),TrialPhaseDiagnostic.available{phaseAutoRun=true;prepareModels()}
    else if CommandLine.arguments.contains("--run-cpu-model-diagnostic"){modelDiagnosticAutoRun=true;prepareModels()}
    else if CommandLine.arguments.contains("--run-file-asr-diagnostic"){fileAsrAutoRun=true;prepareModels()}
    NotificationCenter.default.addObserver(forName:AVAudioSession.interruptionNotification,object:nil,queue:.main){[weak self]_ in self?.invalidateAudio()}
    NotificationCenter.default.addObserver(forName:AVAudioSession.routeChangeNotification,object:nil,queue:.main){[weak self] n in
      guard let reason=n.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,[AVAudioSession.RouteChangeReason.oldDeviceUnavailable.rawValue,AVAudioSession.RouteChangeReason.noSuitableRouteForCategory.rawValue,AVAudioSession.RouteChangeReason.override.rawValue].contains(reason) else{return};self?.invalidateAudio()
    }
  }
  private func button(_ b:UIButton,_ title:String,_ action:Selector){b.setTitle(title,for:.normal);b.titleLabel?.font = .preferredFont(forTextStyle:.headline);b.addTarget(self,action:action,for:.touchUpInside)}
  private func updateButtons(){
    let idle = !active && lifecycle.current == nil && !survey.awaitingRating && !modelQualitySession.awaitingRating
    lifecycleButton.setTitle("12. Lifecycle: "+(lifecycle.next ?? "finished"),for:.normal)
    lifecycleButton.isEnabled=ready && audible && operatorAttested && idle && lifecycle.next != nil
    prepare.isEnabled = !ready && idle;probe.isEnabled=ready && operatorAttested && idle;heard.isEnabled=probeDone && !audible && idle
    microphone.isEnabled=ready && audible && idle;model.isEnabled=ready && audible && idle
    modelQuality.isEnabled=ready && idle && modelQualitySession.canBegin
    for b in modelQualityRatings{b.isEnabled=modelQualitySession.awaitingRating && eligibility.allowed && !active}
    residentDiagnostic.isEnabled=TrialResidentDiagnostic.available && ready && idle && !residentUsed && comparisonLlm != nil
    phaseDiagnostic.isEnabled=TrialPhaseDiagnostic.available && ready && idle && !phaseUsed
    modelDiagnostic.isEnabled=ready && idle && !modelDiagnosticUsed
    fileAsr.isEnabled=ready && idle
    quality.isEnabled=ready && audible && operatorAttested && idle && voiceFixtures.count==12 && survey.nextFixture != nil
    for b in ratings{b.isEnabled=survey.awaitingRating && eligibility.allowed && !active};stopButton.isEnabled=true
  }
  private func saveSurvey(){
    guard !survey.attempts.isEmpty,let voice=surveyVoiceID,let declared=report["radio_attestation_recorded_utc"] as? String else{return}
    let r:[String:Any]=["schema_version":1,"scope":"INTERNAL_IOS_LISTENING_SURVEY","physical_gate_acceptance":"NOT_RUN","acoustic_timing":"NOT_RUN","network_observation":"NOT_RUN","radio_state":"OPERATOR_DECLARED_OFF_AT_BUILD","radio_attestation_recorded_utc":declared,"fixture_sha256":fixtureDigest,"voice_id":voice,"os_build":ProcessInfo.processInfo.operatingSystemVersionString,"updated_utc":ISO8601DateFormatter().string(from:Date()),"attempts":survey.aggregate]
    let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("voice-survey-results.json")
    if let data=try? JSONSerialization.data(withJSONObject:r,options:[.sortedKeys]){try? data.write(to:url,options:.atomic)}
  }
  @discardableResult private func saveModelQuality()->Bool{
    guard let llm,!modelQualitySession.attempts.isEmpty else{return false}
    let r:[String:Any]=["schema_version":1,"scope":"IOS_MODEL_QUALITY_COLLECTION","fixture_manifest_sha256":TrialModelDiagnostic.fixtureDigest,
      "runtime_revision":llm.runtimeRevision,"rating_source":"HUMAN_OPERATOR_UI","quality_scale":"FROZEN_RUBRIC_1_TO_5",
      "raw_text_exported":false,"raw_audio_saved":false,"audio_devices":"NOT_OPENED","physical_gate_acceptance":"NOT_RUN","network_observation":"NOT_RUN",
      "context_tokens":4096,"output_token_limit":256,"threads":2,"sampler":"greedy","enable_thinking":false,
      "model_sha256":llm.model.sha256,"model_bytes":llm.model.bytes,"session_id":modelQualitySessionID,
      "os_build":ProcessInfo.processInfo.operatingSystemVersionString,"updated_utc":ISO8601DateFormatter().string(from:Date()),"attempts":modelQualitySession.aggregate]
    let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("model-quality-results.json")
    do{try JSONSerialization.data(withJSONObject:r,options:[.sortedKeys]).write(to:url,options:.atomic);return true}
    catch{modelQualityNote.text="Quality scores remain in this app session, but saving failed. Keep the app open and report this status.";return false}
  }
  @objc private func runModelQuality(){
    guard ready,!active,!survey.awaitingRating,!modelQualitySession.awaitingRating,eligibility.allowed,let store,let llm,let(ticket,fixture)=modelQualitySession.begin() else{return}
    diagnosticIdleTimer=UIApplication.shared.isIdleTimerDisabled;UIApplication.shared.isIdleTimerDisabled=true
    let cancellation=TrialModelCancellation();modelQualityCancellation=cancellation
    let operation=audioEpoch.begin(),deadline=ProcessInfo.processInfo.systemUptime+120
    active=true;modelQualityRunning=true;modelQualityAnswer.text=nil;modelQualityNote.text="Generating fixed answer \(fixture) of 6. No audio.";updateButtons();saveModelQuality()
    let assets=Bundle.main.bundleURL.appendingPathComponent("TrialAssets")
    installer.async{[weak self] in
      guard let self else{return}
      do{
        let reply=try TrialModelQuality.run(assets:assets,store:store,selection:llm,fixture:fixture,cancellation:cancellation,allowed:{self.audioEpoch.current(operation) && ProcessInfo.processInfo.systemUptime<deadline})
        DispatchQueue.main.async{
          guard self.audioEpoch.current(operation),self.modelQualitySession.finish(ticket) else{return}
          self.audioEpoch.cancel();self.restoreDiagnosticIdleTimer();self.active=false;self.modelQualityRunning=false;self.modelQualityCancellation=nil
          self.modelQualityAnswer.text="Prompt: "+reply.prompt+"\n\nRubric: "+reply.rubric+"\n\nAnswer: "+reply.answer
          self.modelQualityNote.text="Rate answer \(fixture) against its rubric: 1 incorrect/unusable, 5 correct/clear. Text clears after rating."
          self.saveModelQuality();self.updateButtons()
        }
      }catch{DispatchQueue.main.async{
        guard self.audioEpoch.current(operation) else{return}
        self.audioEpoch.cancel();self.restoreDiagnosticIdleTimer();self.active=false;self.modelQualityRunning=false;self.modelQualityCancellation=nil
        _ = self.modelQualitySession.fail(ticket);self.modelQualityAnswer.text=nil
        self.modelQualityNote.text=self.modelQualitySession.canBegin ? "Fixed answer generation failed or its text guard rejected it. No score inferred. Retry, or report repeated failure." : "Three attempts exhausted for this answer. Keep the app open and report the failure; no quality score inferred."
        self.saveModelQuality();self.updateButtons()
      }}
    }
  }
  @objc private func rateModelQuality(_ sender:UIButton){
    guard eligibility.allowed,!active,modelQualitySession.rate(sender.tag) else{return}
    modelQualityAnswer.text=nil
    modelQualityNote.text=modelQualitySession.nextFixture==nil ? "All six model answers rated. Leave the app open for aggregate export." : "Rating recorded. Review the next fixed answer."
    saveModelQuality();updateButtons()
  }
  private func saveModelDiagnostic(_ phase:String,_ rows:[[String:Any]]){
    guard let llm else{return}
    let r:[String:Any]=["schema_version":1,"scope":"IOS_CPU_MODEL_DIAGNOSTIC","phase":phase,"process_id":modelDiagnosticProcess,
      "model_sha256":llm.model.sha256,"model_bytes":llm.model.bytes,"runtime_revision":llm.runtimeRevision,
      "fixture_manifest_sha256":TrialModelDiagnostic.fixtureDigest,"os_build":ProcessInfo.processInfo.operatingSystemVersionString,
      "physical_memory_bytes":ProcessInfo.processInfo.physicalMemory,"updated_utc":ISO8601DateFormatter().string(from:Date()),
      "context_tokens":4096,"output_token_limit":256,"threads":2,"sampler":"greedy","enable_thinking":false,"backend":"CPU",
      "model_open":"FRESH_HANDLE_PER_PROMPT_OS_CACHES_UNCONTROLLED","memory_scope":"PROCESS_LIFETIME_INCLUDING_PREPARATION",
      "timing_scope":"BEGIN_INCLUDES_TOKENIZATION_CONTEXT_AND_PREFILL_FIRST_PIECE_INCLUDES_NATIVE_NEXT_DECODE",
      "microphone":"NOT_OPENED","speaker":"NOT_OPENED","raw_text_exported":false,
      "network_observation":"NOT_RUN","quality":"NOT_RUN","physical_gate_acceptance":"NOT_RUN","cases":rows]
    let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("cpu-model-results.json")
    if let data=try? JSONSerialization.data(withJSONObject:r,options:[.sortedKeys]){try? data.write(to:url,options:.atomic)}
  }
  private func saveResidentDiagnostic(_ phase:String){
    guard let llm,let comparisonLlm else{return}
    let pins=[llm,comparisonLlm].enumerated().map{index,s in ["candidate_index":index,"model_sha256":s.model.sha256,"model_bytes":s.model.bytes] as [String:Any]}
    let r:[String:Any]=["schema_version":2,"scope":"IOS_RESIDENT_MODEL_COMPARISON","phase":phase,"process_id":residentProcess,"model_pins":pins,
      "runtime_revision":llm.runtimeRevision,"fixture_manifest_sha256":TrialModelDiagnostic.fixtureDigest,
      "os_build":ProcessInfo.processInfo.operatingSystemVersionString,"physical_memory_bytes":ProcessInfo.processInfo.physicalMemory,
      "updated_utc":ISO8601DateFormatter().string(from:Date()),"context_tokens":4096,"output_token_limit":256,"threads":2,"sampler":"greedy","enable_thinking":false,"backend":"CPU",
      "model_open":"EXPLICIT_SCOPED_MODEL_WEIGHTS_RESIDENCY_THREE_FRESH_GENERATIONS","memory_scope":"PROCESS_LIFETIME_INCLUDING_PREPARATION",
      "cold_start_scope":"MODEL_UNLOADED_AT_GROUP_START_OS_CACHES_UNCONTROLLED_PROCESS_REUSED",
      "warm_scope":"GENERIC_MODEL_WEIGHTS_ONLY_FRESH_CONTEXT_KV_SAMPLER_EACH_GENERATION",
      "candidate_order":"1P7_THEN_0P6_ODD_FIXTURES_REVERSED_EVEN_FIXTURES",
      "thermal_policy":"WAIT_BELOW_SERIOUS_BEFORE_EACH_SAMPLE_MAX_300S",
      "timing_clock":"std::chrono::steady_clock","battery_scope":"OS_LEVEL_BEFORE_AFTER_USB_CONNECTED_NOT_ENERGY_MEASUREMENT",
      "microphone":"NOT_OPENED","speaker":"NOT_OPENED","raw_text_exported":false,"network_observation":"NOT_RUN","quality":"NOT_RUN","physical_gate_acceptance":"NOT_RUN","cases":residentRows]
    let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("resident-model-results.json")
    do{let data=try JSONSerialization.data(withJSONObject:r,options:[.sortedKeys]);try data.write(to:url,options:.atomic)}
    catch{status.text="Resident report could not be saved. Keep the app open and report the failure."}
  }
  @objc private func runResidentDiagnostic(){
    guard TrialResidentDiagnostic.available,ready,!active,!survey.awaitingRating,!modelQualitySession.awaitingRating,!residentUsed,eligibility.allowed,let store,let llm,let comparisonLlm else{return}
    residentUsed=true;residentRunning=true;active=true;residentRows=[]
    diagnosticIdleTimer=UIApplication.shared.isIdleTimerDisabled;UIApplication.shared.isIdleTimerDisabled=true
    batteryMonitoring=UIDevice.current.isBatteryMonitoringEnabled;UIDevice.current.isBatteryMonitoringEnabled=true
    let cancellation=TrialModelCancellation();diagnosticCancellation=cancellation
    let operation=audioEpoch.begin(),deadline=ProcessInfo.processInfo.systemUptime+3600
    status.text="Running 36 alternating model samples, with recorded nominal/fair sample starts. No audio.";saveResidentDiagnostic("RUNNING");updateButtons()
    let assets=Bundle.main.bundleURL.appendingPathComponent("TrialAssets")
    installer.async{[weak self] in
      guard let self else{return}
      do{
        let rows=try TrialResidentDiagnostic.run(assets:assets,store:store,selections:[llm,comparisonLlm],cancellation:cancellation,
          allowed:{self.audioEpoch.current(operation) && ProcessInfo.processInfo.systemUptime<deadline},progress:{rows,note in
            DispatchQueue.main.async{guard self.audioEpoch.current(operation) else{return};self.residentRows=rows;self.status.text=note;self.saveResidentDiagnostic("RUNNING")}
          })
        DispatchQueue.main.async{guard self.audioEpoch.current(operation) else{return};self.residentRows=rows;self.audioEpoch.cancel();self.active=false;self.residentRunning=false;self.diagnosticCancellation=nil;self.restoreDiagnosticIdleTimer();self.status.text="All 36 resident comparison samples completed. Leave the app open for export.";self.saveResidentDiagnostic("COMPLETED");self.updateButtons()}
      }catch{
        let phase=(error as? TrialResidentFailure) == .thermalLimit ? "THERMAL_LIMIT":"INFERENCE_FAILED"
        DispatchQueue.main.async{guard self.audioEpoch.current(operation) else{return};self.audioEpoch.cancel();self.active=false;self.residentRunning=false;self.diagnosticCancellation=nil;self.restoreDiagnosticIdleTimer();self.status.text=phase=="THERMAL_LIMIT" ? "Thermal limit reached. Completed samples retained; allow the phone to cool before another run.":"Resident comparison failed. Completed samples retained; no acceptance inferred.";self.saveResidentDiagnostic(phase);self.updateButtons()}
      }
    }
  }
  private func savePhaseDiagnostic(_ phase:String){
    guard let llm else{return}
    let r:[String:Any]=["schema_version":1,"scope":"IOS_NATIVE_PHASE_RELOAD_DIAGNOSTIC","phase":phase,"process_id":phaseProcess,
      "model_sha256":llm.model.sha256,"model_bytes":llm.model.bytes,"runtime_revision":llm.runtimeRevision,
      "fixture_manifest_sha256":TrialModelDiagnostic.fixtureDigest,"os_build":ProcessInfo.processInfo.operatingSystemVersionString,
      "physical_memory_bytes":ProcessInfo.processInfo.physicalMemory,"updated_utc":ISO8601DateFormatter().string(from:Date()),
      "context_tokens":4096,"output_token_limit":256,"threads":2,"sampler":"greedy","enable_thinking":false,"backend":"CPU",
      "model_open":"FRESH_HANDLE_EVERY_SAMPLE_THREE_ROUNDS_OS_CACHES_UNCONTROLLED",
      "cold_cache":"NOT_ESTABLISHED","resident_model_warm":"NOT_RUN","memory_scope":"PROCESS_LIFETIME_INCLUDING_PREPARATION",
      "timing_clock":"std::chrono::steady_clock","battery_scope":"OS_LEVEL_BEFORE_AFTER_USB_CONNECTED_NOT_ENERGY_MEASUREMENT",
      "microphone":"NOT_OPENED","speaker":"NOT_OPENED","raw_text_exported":false,"network_observation":"NOT_RUN",
      "quality":"NOT_RUN","physical_gate_acceptance":"NOT_RUN","cases":phaseRows]
    let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("native-phase-results.json")
    do{let data=try JSONSerialization.data(withJSONObject:r,options:[.sortedKeys]);try data.write(to:url,options:.atomic)}
    catch{status.text="Phase report could not be saved. Keep the app open and report the failure."}
  }
  @objc private func runPhaseDiagnostic(){
    guard TrialPhaseDiagnostic.available,ready,!active,!survey.awaitingRating,!modelQualitySession.awaitingRating,!phaseUsed,eligibility.allowed,let store,let llm else{return}
    phaseUsed=true;phaseRunning=true;active=true;phaseRows=[]
    diagnosticIdleTimer=UIApplication.shared.isIdleTimerDisabled;UIApplication.shared.isIdleTimerDisabled=true
    batteryMonitoring=UIDevice.current.isBatteryMonitoringEnabled;UIDevice.current.isBatteryMonitoringEnabled=true
    let cancellation=TrialModelCancellation();diagnosticCancellation=cancellation
    let operation=audioEpoch.begin(),deadline=ProcessInfo.processInfo.systemUptime+1800
    status.text="Running 18 fresh-handle samples. OS caches uncontrolled; no audio.";savePhaseDiagnostic("RUNNING");updateButtons()
    let assets=Bundle.main.bundleURL.appendingPathComponent("TrialAssets")
    installer.async{[weak self] in
      guard let self else{return}
      do{
        let rows=try TrialPhaseDiagnostic.run(assets:assets,store:store,selection:llm,cancellation:cancellation,
          allowed:{self.audioEpoch.current(operation) && ProcessInfo.processInfo.systemUptime<deadline},progress:{rows in
            DispatchQueue.main.async{guard self.audioEpoch.current(operation) else{return};self.phaseRows=rows;self.status.text="Native phase samples: \(rows.count)/18. No audio.";self.savePhaseDiagnostic("RUNNING")}
          })
        DispatchQueue.main.async{guard self.audioEpoch.current(operation) else{return};self.phaseRows=rows;self.audioEpoch.cancel();self.active=false;self.phaseRunning=false;self.diagnosticCancellation=nil;self.restoreDiagnosticIdleTimer();self.status.text="All 18 phase samples completed. Leave the app open for export.";self.savePhaseDiagnostic("COMPLETED");self.updateButtons()}
      }catch{DispatchQueue.main.async{guard self.audioEpoch.current(operation) else{return};self.audioEpoch.cancel();self.active=false;self.phaseRunning=false;self.diagnosticCancellation=nil;self.restoreDiagnosticIdleTimer();self.status.text="Phase diagnostic failed. Completed samples retained; no acceptance inferred.";self.savePhaseDiagnostic("INFERENCE_FAILED");self.updateButtons()}}
    }
  }
  private func restoreDiagnosticIdleTimer(){
    if let previous=batteryMonitoring{UIDevice.current.isBatteryMonitoringEnabled=previous;batteryMonitoring=nil}
    if let previous=diagnosticIdleTimer{UIApplication.shared.isIdleTimerDisabled=previous;diagnosticIdleTimer=nil}
  }
  @objc private func runModelDiagnostic(){
    guard ready,!active,!survey.awaitingRating,!modelQualitySession.awaitingRating,!modelDiagnosticUsed,eligibility.allowed,let store,let llm else{return}
    diagnosticIdleTimer=UIApplication.shared.isIdleTimerDisabled;UIApplication.shared.isIdleTimerDisabled=true
    modelDiagnosticUsed=true;modelDiagnosticRunning=true;active=true
    let cancellation=TrialModelCancellation();diagnosticCancellation=cancellation
    let operation=audioEpoch.begin(),deadline=ProcessInfo.processInfo.systemUptime+600
    status.text="Running six fixed CPU prompts. No microphone or speaker is active.";updateButtons();saveModelDiagnostic("RUNNING",[])
    let assets=Bundle.main.bundleURL.appendingPathComponent("TrialAssets")
    installer.async{[weak self] in
      guard let self else{return}
      do{
        let rows=try TrialModelDiagnostic.run(assets:assets,store:store,selection:llm,cancellation:cancellation,allowed:{self.audioEpoch.current(operation) && ProcessInfo.processInfo.systemUptime<deadline})
        DispatchQueue.main.async{guard self.audioEpoch.current(operation) else{return};self.audioEpoch.cancel();self.active=false;self.restoreDiagnosticIdleTimer();self.modelDiagnosticRunning=false;self.diagnosticCancellation=nil;self.saveModelDiagnostic("COMPLETED",rows);self.status.text="Six CPU prompts completed. Quality and independent network verification remain unrun. Restart the app before another model diagnostic.";self.updateButtons()}
      }catch{DispatchQueue.main.async{guard self.audioEpoch.current(operation) else{return};self.audioEpoch.cancel();self.active=false;self.restoreDiagnosticIdleTimer();self.modelDiagnosticRunning=false;self.diagnosticCancellation=nil;self.saveModelDiagnostic("INFERENCE_FAILED",[]);self.status.text="CPU diagnostic failed. No acceptance inferred. Restart before retrying.";self.updateButtons()}}
    }
  }
  private func saveFileAsr(_ phase:String,_ rows:[[String:Any]]){
    let r:[String:Any]=["schema_version":1,"scope":"IOS_DEVICE_FILE_ASR_DIAGNOSTIC","phase":phase,"input_kind":"FROZEN_SYNTHETIC_FILES","microphone":"NOT_OPENED","physical_quality_acceptance":"NOT_RUN","acoustic_timing":"NOT_RUN","raw_text_exported":false,"fixture_manifest_sha256":TrialFileAsr.fixtureDigest,"os_build":ProcessInfo.processInfo.operatingSystemVersionString,"physical_memory_bytes":ProcessInfo.processInfo.physicalMemory,"updated_utc":ISO8601DateFormatter().string(from:Date()),"cases":rows]
    let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("file-asr-results.json")
    if let data=try? JSONSerialization.data(withJSONObject:r,options:[.sortedKeys]){try? data.write(to:url,options:.atomic)}
  }
  @objc private func runFileAsr(){
    guard ready,!active,!survey.awaitingRating,!modelQualitySession.awaitingRating,eligibility.allowed,let store,let asr else{return}
    let operation=audioEpoch.begin(),deadline=ProcessInfo.processInfo.systemUptime+180
    active=true;fileAsrRunning=true;updateButtons();status.text="Running six fixed ASR files. No microphone or speaker is active.";saveFileAsr("RUNNING",[])
    let assets=Bundle.main.bundleURL.appendingPathComponent("TrialAssets")
    installer.async{[weak self] in
      guard let self else{return}
      do{
        let rows=try TrialFileAsr.run(assets:assets,store:store,selection:asr,allowed:{self.audioEpoch.current(operation) && ProcessInfo.processInfo.systemUptime<deadline})
        DispatchQueue.main.async{guard self.audioEpoch.current(operation) else{return};self.audioEpoch.cancel();self.active=false;self.fileAsrRunning=false;self.saveFileAsr("COMPLETED",rows);self.status.text="Six-file ASR diagnostic completed. Runtime and edit counts only; physical microphone quality remains unrun.";self.updateButtons()}
      }catch{DispatchQueue.main.async{guard self.audioEpoch.current(operation) else{return};self.audioEpoch.cancel();self.active=false;self.fileAsrRunning=false;self.saveFileAsr("INFERENCE_FAILED",[]);self.status.text="File ASR diagnostic failed. No success inferred.";self.updateButtons()}}
    }
  }
  @objc private func playQuality(){
    guard ready,audible,operatorAttested,eligibility.allowed,!active,!survey.awaitingRating,voiceFixtures.count==12,
      let id=surveyVoiceID ?? selectedVoice?.identifier,let voice=AVSpeechSynthesisVoice(identifier:id),
      !voice.voiceTraits.contains(.isPersonalVoice),let (ticket,fixture)=survey.begin() else{return}
    surveyVoiceID=id;surveyTicket=ticket;active=true;updateButtons()
    do{try AVAudioSession.sharedInstance().setCategory(.playback,mode:.default);try AVAudioSession.sharedInstance().setActive(true)}catch{stop();qualityNote.text="Listening survey audio session failed. Attempt retained.";return}
    let u=AVSpeechUtterance(string:voiceFixtures[fixture-1]);u.voice=voice;u.volume=0.4;surveyUtterance=u
    qualityNote.text="Phrase \(fixture)/12 — listen, then rate 1–5 after playback. No acoustic timing is measured."
    saveSurvey();synth.speak(u)
    timer?.invalidate();timer=Timer.scheduledTimer(withTimeInterval:45,repeats:false){[weak self,weak u]_ in
      guard let self,let u,self.surveyUtterance===u else{return};self.stop();self.qualityNote.text="Listening phrase timed out. Attempt retained; no rating assigned."
    }
  }
  @objc private func rateQuality(_ sender:UIButton){
    guard eligibility.allowed,!active,survey.rate(sender.tag) else{return};saveSurvey()
    qualityNote.text=survey.nextFixture==nil ? "All 12 phrases rated. Listening ratings only; acoustic timing, traffic verification and physical acceptance remain NOT_RUN.":"Rating saved. Tap Play next listening-survey phrase."
    updateButtons()
  }
  private func save(){
    // Exact owned-app aggregate file; never raw speech, prompt, transcript or model reply.
    let dir=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0]
    report["updated_utc"]=ISO8601DateFormatter().string(from:Date())
    if let bytes=try? JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]){try? bytes.write(to:dir.appendingPathComponent("trial-results.json"),options:.atomic)}
  }
  private func fail(_ code:String){if lifecycle.current != nil{lifecycle.failed();saveLifecycle()};lifecycleUtterance=nil;lifecycleTimer?.invalidate();stop();report["phase"]=code;status.text="Trial stopped: "+code;save()}
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
          return ["id":id,"filename":name,"role":id.hasPrefix("llm") ? "llm":id=="vad" ? "vad":name=="tokenizer.bin" ? "tokenizer":"asr",
            "url":"https://models.example.test/"+name,"sha256":r["sha256"]!,"bytes":r["bytes"]!,"license":id.hasPrefix("llm") ? "Apache-2.0":"MIT","licenseEvidence":evidence]}
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
        let pins=try rows.filter{!(($0["id"] as? String ?? "").hasPrefix("llm"))}.map{try SpeechArtifactPin(id:$0["id"] as! String,filename:$0["filename"] as! String,sha256:$0["sha256"] as! String,bytes:($0["bytes"] as! NSNumber).int64Value,licenseEvidence:evidence)}
        let v=try SpeechPackSelection(packID:"physical-lab",runtimeRevision:runtime,kind:.vad,pins:pins.filter{$0.id=="vad"})
        let a=try SpeechPackSelection(packID:"physical-lab",runtimeRevision:runtime,kind:.asr,pins:pins.filter{$0.id != "vad"})
        let last=rows.first{$0["id"] as? String == "llm"}!;let l=try LlmPackSelection(packID:"physical-lab",runtimeRevision:runtime,model:LlmArtifactPin(id:"llm",sha256:last["sha256"] as! String,bytes:(last["bytes"] as! NSNumber).int64Value,licenseEvidence:evidence))
        let comparison:LlmPackSelection?
        if let secondary=rows.first(where:{$0["id"] as? String == "llm-06b"}){
          comparison=try LlmPackSelection(packID:"physical-lab",runtimeRevision:runtime,model:LlmArtifactPin(id:"llm-06b",sha256:secondary["sha256"] as! String,bytes:(secondary["bytes"] as! NSNumber).int64Value,licenseEvidence:evidence))
        }else{comparison=nil}
        DispatchQueue.main.async{guard self.modelEpoch.current(preparation) else{return};self.modelCancel=nil;self.store=store;self.vad=v;self.asr=a;self.llm=l;self.comparisonLlm=comparison;self.ready=true;self.status.text="Models verified. Play the voice probe next.";self.report["phase"]="MODELS_READY";self.save();self.updateButtons();if self.residentAutoRun{self.residentAutoRun=false;self.runResidentDiagnostic()}else if self.phaseAutoRun{self.phaseAutoRun=false;self.runPhaseDiagnostic()}else if self.modelDiagnosticAutoRun{self.modelDiagnosticAutoRun=false;self.runModelDiagnostic()}else if self.fileAsrAutoRun{self.fileAsrAutoRun=false;self.runFileAsr()}}
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
  func speechSynthesizer(_ synthesizer:AVSpeechSynthesizer,didFinish utterance:AVSpeechUtterance){
    if utterance===lifecycleUtterance { lifecycle.failed();lifecycleUtterance=nil;stop();saveLifecycle();return }
    if utterance===surveyUtterance{
      guard eligibility.allowed,let ticket=surveyTicket,survey.finish(ticket) else{return}
      surveyUtterance=nil;surveyTicket=nil;timer?.invalidate();timer=nil;active=false
      try? AVAudioSession.sharedInstance().setActive(false,options:.notifyOthersOnDeactivation)
      qualityNote.text="Playback completed. Rate intelligibility 1–5 (1 unintelligible, 5 fully clear).";saveSurvey();updateButtons();return
    };guard utterance===probeUtterance,eligibility.allowed else{return};probeUtterance=nil;active=false;probeDone=true;report["sdk_probe_completed"]=true;report["phase"]="VOICE_PROBE_SDK_COMPLETED";status.text="If you heard the complete phrase, tap confirmation. SDK completion alone does not prove hearing.";save();updateButtons()}
  func speechSynthesizer(_ synthesizer:AVSpeechSynthesizer,didCancel utterance:AVSpeechUtterance){if utterance===surveyUtterance{stop();return};guard utterance===probeUtterance else{return};probeUtterance=nil;active=false;updateButtons()}
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
        if self.lifecycle.current != nil{self.lifecycle.failed();self.saveLifecycle()}
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
  private func lifecycleInstruction()->String {
    guard let id=lifecycle.current else{return lifecycle.complete ? "Six lifecycle cases observed. Leave the app open for export." : "Lifecycle attempt retained. Replay/confirm the offline probe if needed, then start the next check."}
    if id.hasSuffix("_stop"){return "Audio active: tap Stop and clear now. Then wait for verification."}
    if id.hasSuffix("_lock"){return "Audio active: lock with the side button, wait 5 seconds, unlock and reopen Eilo. No audio should resume."}
    return "Audio active: go to the Home Screen, wait 5 seconds, then reopen Eilo. No audio should resume."
  }
  private func saveLifecycle(){
    var r=lifecycle.aggregate
    r["process_session"]=lifecycleSession;r["os_build"]=ProcessInfo.processInfo.operatingSystemVersionString
    r["physical_memory_bytes"]=ProcessInfo.processInfo.physicalMemory
    r["updated_utc"]=ISO8601DateFormatter().string(from:Date())
    let url=FileManager.default.urls(for:.documentDirectory,in:.userDomainMask)[0].appendingPathComponent("lifecycle-results.json")
    do{try JSONSerialization.data(withJSONObject:r,options:[.sortedKeys]).write(to:url,options:.atomic)}
    catch{lifecycleNote.text="Lifecycle export failed. Keep the app open; no success is inferred."}
  }
  private func lifecycleStopped()->Bool {
    !active && speech == nil && turn == nil && transcript.text == nil && lifecycleUtterance == nil && !synth.isSpeaking && !synth.isPaused && !micController.captureIsPending && !modelController.captureIsPending && micController.state == .stopped && modelController.state == .stopped && (report["audio_session_deactivated"] as? Bool == true) && (lifecycleOperation.map{!audioEpoch.current($0)} ?? true)
  }
  private func verifyLifecycleAfterDelay(){
    lifecycleTimer?.invalidate()
    lifecycleTimer=Timer.scheduledTimer(withTimeInterval:2,repeats:false){[weak self]_ in
      guard let self,self.lifecycle.verifying else{return}
      self.lifecycle.verified(stillStopped:self.lifecycleStopped());self.lifecycleOperation=nil
      self.lifecycleNote.text=self.lifecycleInstruction();self.saveLifecycle();self.updateButtons()
    }
  }
  private func stopLifecycle(_ event:String){
    let pending=lifecycle.current != nil
    lifecycleUtterance=nil;lifecycleTimer?.invalidate();lifecycleTimer=nil
    stop()
    if pending {
      let verify=lifecycle.stoppedBy(event,stopped:lifecycleStopped())
      lifecycleNote.text=lifecycle.waitingForReturn ? "Stopped. Return to Eilo for the no-resume check." : lifecycleInstruction()
      saveLifecycle();updateButtons();if verify || lifecycle.verifying{verifyLifecycleAfterDelay()}
    }
  }
  @objc private func operatorStop(){stopLifecycle("STOP_BUTTON")}
  @objc private func startLifecycle(){
    guard ready,audible,operatorAttested,!active,eligibility.allowed,let voice=selectedVoice,let id=lifecycle.begin() else{return}
    lifecycleNote.text="Starting lifecycle check. Wait until audio is active.";saveLifecycle()
    lifecycleOperation=audioEpoch.begin();let lifecycleTicket=lifecycleOperation;active=true;updateButtons()
    if id.hasPrefix("capture_") {
      controller=micController
      guard controller.dispatch(.start) else{fail("CAPTURE_START_DENIED");return}
      report["phase"]="CAPTURE_START_REQUESTED";save()
      let deadline=ProcessInfo.processInfo.systemUptime+35
      lifecycleTimer=Timer.scheduledTimer(withTimeInterval:0.1,repeats:true){[weak self]_ in
        guard let self,self.lifecycleOperation == lifecycleTicket,self.lifecycle.current?.hasPrefix("capture_") == true else{return}
        if self.controller.state == .error || (self.controller.state == .stopped && !self.controller.captureIsPending){self.fail("CAPTURE_OR_REPLY_FAILED");return}
        if self.controller.state == .standby,self.lifecycle.observedActive(){
          self.lifecycleNote.text=self.lifecycleInstruction();self.status.text="Microphone active. Remain quiet and perform the lifecycle action. No recognition or recording is attached."
          self.report["phase"]="MICROPHONE_SPEAK_NOW";self.report["microphone_permission_granted"]=self.permission.status() == .granted;self.save();self.saveLifecycle()
        }
        if ProcessInfo.processInfo.systemUptime>deadline{self.fail("TRIAL_TIMEOUT")}
      }
      return
    }
    do{try AVAudioSession.sharedInstance().setCategory(.playback,mode:.default);try AVAudioSession.sharedInstance().setActive(true)}
    catch{lifecycle.failed();stop();saveLifecycle();return}
    let phrase="This is a fixed offline Eilo lifecycle test. Use the requested action to stop this test. "
    let u=AVSpeechUtterance(string:String(repeating:phrase,count:8));u.voice=voice;u.volume=0.4;lifecycleUtterance=u;synth.speak(u)
    lifecycleTimer=Timer.scheduledTimer(withTimeInterval:0.1,repeats:true){[weak self]_ in
      guard let self,self.lifecycleOperation == lifecycleTicket,self.lifecycle.current != nil else{return}
      if self.synth.isSpeaking,self.lifecycle.observedActive(){self.lifecycleNote.text=self.lifecycleInstruction();self.saveLifecycle()}
    }
    DispatchQueue.main.asyncAfter(deadline:.now()+35){[weak self,weak u] in
      guard let self,let u,self.lifecycleUtterance===u else{return}
      self.lifecycle.failed();self.lifecycleUtterance=nil;self.stop();self.saveLifecycle()
    }
  }
  @objc private func stop(){lifecycleTimer?.invalidate();lifecycleTimer=nil;lifecycleUtterance=nil;let qualityPending=modelQualityRunning || modelQualitySession.awaitingRating;modelQualityCancellation?.cancel();modelQualityCancellation=nil;modelQualityRunning=false;modelQualitySession.cancel();modelQualityAnswer.text=nil;if qualityPending{modelQualityNote.text=modelQualitySession.canBegin ? "Review stopped. Pending answer/rating cleared; prior scores retained. Replay to rate." : "Review stopped or attempt limit reached. Prior scores retained; keep the app open for export."};saveModelQuality();restoreDiagnosticIdleTimer();residentAutoRun=false;if residentRunning{saveResidentDiagnostic("CANCELLED");residentRunning=false};phaseAutoRun=false;if phaseRunning{savePhaseDiagnostic("CANCELLED");phaseRunning=false};modelDiagnosticAutoRun=false;diagnosticCancellation?.cancel();diagnosticCancellation=nil;if modelDiagnosticRunning{saveModelDiagnostic("CANCELLED",[]);modelDiagnosticRunning=false};fileAsrAutoRun=false;if fileAsrRunning{saveFileAsr("CANCELLED",[]);fileAsrRunning=false};if survey.awaitingRating || surveyUtterance != nil{qualityNote.text="Listening survey stopped. Pending rating revoked; replay the phrase to rate it. Attempts are retained."};survey.cancel();surveyUtterance=nil;surveyTicket=nil;saveSurvey();audioEpoch.cancel();modelEpoch.cancel();modelCancel?.cancel();modelCancel=nil;probeUtterance=nil;timer?.invalidate();timer=nil;_ = micController?.stop();_ = modelController?.stop();speech?.close();speech=nil;turn=nil;_ = synth.stopSpeaking(at:.immediate);active=false;attached=false;transcript.text=nil;do{try AVAudioSession.sharedInstance().setActive(false,options:.notifyOthersOnDeactivation);report["audio_session_deactivated"]=true}catch{report["audio_session_deactivated"]=false};report["phase"]="STOPPED_CONTENT_CLEARED";save();updateButtons()}
  private func invalidateAudio(_ event:String="AUDIO_INTERRUPTION_OR_ROUTE"){stopLifecycle(event);audible=false;probeDone=false;updateButtons()}
  func applicationWillResignActive(_ application:UIApplication){eligibility.visible=false;report["foreground"]=false;invalidateAudio("SCENE_RESIGNED")}
  func applicationDidBecomeActive(_ application:UIApplication){eligibility.visible=true;eligibility.protectedData(application.isProtectedDataAvailable);controller.permissionChanged();report["foreground"]=true;save();if lifecycle.returned(){saveLifecycle();verifyLifecycleAfterDelay()}}
  func applicationProtectedDataWillBecomeUnavailable(_ application:UIApplication){eligibility.protectedData(false);invalidateAudio("PROTECTED_DATA_UNAVAILABLE");_ = controller.privacyTransition(.lock)}
  func applicationProtectedDataDidBecomeAvailable(_ application:UIApplication){eligibility.protectedData(true);_ = controller.privacyTransition(.unlock)}
}

final class TrialScene:UIResponder,UIWindowSceneDelegate {
  func scene(_ scene:UIScene,willConnectTo session:UISceneSession,options:UIScene.ConnectionOptions){guard let windowScene=scene as? UIWindowScene else{return};(UIApplication.shared.delegate as? TrialApp)?.configureScene(windowScene)}
  func sceneWillResignActive(_ scene:UIScene){(UIApplication.shared.delegate as? TrialApp)?.applicationWillResignActive(UIApplication.shared)}
  func sceneDidBecomeActive(_ scene:UIScene){(UIApplication.shared.delegate as? TrialApp)?.applicationDidBecomeActive(UIApplication.shared)}
  func sceneDidDisconnect(_ scene:UIScene){(UIApplication.shared.delegate as? TrialApp)?.applicationWillResignActive(UIApplication.shared)}
}
