import Foundation
import CryptoKit

// Synthetic token fixtures only: no OS permission request or audio activation.
struct ProbePermission:MicrophonePermissionAdapter {
  func status()->MicrophonePermission{.granted}
  func request(_ completion:@escaping(MicrophonePermission)->Void){completion(.granted)}
}
struct ProbeModels:ModelReadinessAdapter{func status()->ModelStatus{.ready}}
final class ProbeEffects:ControllerEffects {
  func startCapture()throws->Bool{true}
  func releaseCapture()throws{}
  func cancelWork()throws{}
  func clearVolatileContext()throws{}
  func playClause(_ clause:String)throws{}
}
// Ephemeral lab signing only; never a production key, license approval or model installation.
final class ProbeSignedVad {
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
  let key=P256.Signing.PrivateKey(),runtime=String(repeating:"a",count:40),evidence=String(repeating:"c",count:64)
  let store:PackStore,pin:SpeechArtifactPin,source:URL
  var lease:SpeechPackLease!
  init(model:String)throws {
    source=URL(fileURLWithPath:model)
    store=PackStore(root:root,trust:["lab-key":key.publicKey.derRepresentation],runtime:runtime,licenseEvidence:[evidence])
    pin=try SpeechArtifactPin(id:"vad",filename:"silero.onnx",sha256:"6b99cbfd39246b6706f98ec13c7c50c6b299181f2474fa05cbc8046acc274396",bytes:2313101,licenseEvidence:evidence)
    try activate(1);lease=try SpeechPackLease.resolve(store:store,selection:selection())
  }
  func selection()throws->SpeechPackSelection{try SpeechPackSelection(packID:"lab-vad",runtimeRevision:runtime,kind:.vad,pins:[pin])}
  func activate(_ revision:Int)throws {
    let artifact:[String:Any]=["id":pin.id,"filename":pin.filename,"role":"vad","url":"https://models.example.test/silero.onnx","sha256":pin.sha256,"bytes":pin.bytes,"license":"MIT","licenseEvidence":evidence]
    let data=try JSONSerialization.data(withJSONObject:["schema":1,"packId":"lab-vad","revision":revision,"runtimeRevision":runtime,"minAndroid":35,"minIos":18,"artifacts":[artifact]],options:[.sortedKeys,.withoutEscapingSlashes])
    let pack=try VerifiedPack.verify(payload:data,signature:key.signature(for:data).derRepresentation,keyID:"lab-key",algorithm:"ES256",trust:["lab-key":key.publicKey.derRepresentation],runtime:runtime)
    try store.activate(pack,proofs:[VerifiedArtifact.verify(pack,index:0,file:source)],cancel:PackCancellation())
  }
  deinit{lease?.close();try? FileManager.default.removeItem(at:root)}
}
@main struct NativeVadCaptureProbe {
  static func require(_ value:Bool){if !value{exit(2)}}
  static func main() throws {
    require(CommandLine.arguments.count==2)
    let model=CommandLine.arguments[1],base=NativeVadAPI.linked
    let signed=try ProbeSignedVad(model:model)
    let worker=DispatchQueue(label:"eilo.synthetic.vad.capture"),key=DispatchSpecificKey<Bool>()
    worker.setSpecific(key:key,value:true)
    var valid=true,revokeOnClose=false,stopDuring=false
    var stop:()->Void={}
    var opens=0,closes=0,calls=0,failures=0
    var events=[VadCaptureOutcome](),asrOpens=0
    var ownedAudio:VadAsrHandoff?
    let controller=NativeController(effects:ProbeEffects(),permission:ProbePermission(),models:ProbeModels())
    require(controller.dispatch(.start));let token=controller.token!

    let api=NativeVadAPI(create:{path in
      require(DispatchQueue.getSpecific(key:key)==true)
      let h=base.create(path);if h != nil{opens+=1};return h
    },process:{h,pcm,final in
      require(DispatchQueue.getSpecific(key:key)==true);calls+=1
      let frame=base.process(h,pcm,final);if stopDuring{stop()};return frame
    },destroy:{h in
      require(DispatchQueue.getSpecific(key:key)==true);closes+=1;base.destroy(h)
      if revokeOnClose{valid=false}
    })
    func transport(withAudio:Bool=false,rate:Int=16000)->VadCaptureTransport {
      let factory:(()->VadAsrHandoff)?=withAudio ? {
        let owner=VadAsrHandoff(token:token,allowed:{valid},open:{asrOpens+=1;throw AsrFailure.unavailable})
        ownedAudio=owner;return owner
      }:nil
      return
      VadCaptureTransport(schedule:{worker.async(execute:$0)},verified:{valid},
        open:{try signed.lease.openVad(allowed:{valid},api:api)},
        output:{value,current in require(current());events.append(value)},failure:{current in require(current());failures+=1},audioFactory:factory,sourceRate:rate)
    }
    func feed(_ d:VadCaptureTransport,count:Int=320,rate:Int=16000) {
      require([Float](repeating:0,count:count).withUnsafeBufferPointer{d.submit($0,sampleRate:rate)})
      worker.sync{}
    }
    let quiet=transport(withAudio:true)
    for _ in 0..<250{feed(quiet)}
    require(events.count==1 && events[0].result == .noSpeech && events[0].totalSamples==80000 && events[0].lastChunkConsumed==320)
    require(quiet.retainedSamples==0 && asrOpens==0 && ownedAudio?.retainedSamples==0);quiet.close();worker.sync{}
    let eof=transport();feed(eof,count:7);eof.finish();worker.sync{}
    require(events.count==2 && events[1].result == .incomplete && events[1].totalSamples==7)
    eof.close();worker.sync{}
    let revoked=transport();stop={revoked.close()};stopDuring=true;feed(revoked,count:512)
    require(events.count==2 && failures==0 && !revoked.current());stopDuring=false;stop={}
    let idle=transport();feed(idle,count:512);let before=closes;idle.close();worker.sync{}
    require(closes==before+1 && !idle.current() && idle.retainedSamples==0)
    let cleanup=transport();feed(cleanup,count:7);revokeOnClose=true;cleanup.finish();worker.sync{}
    require(events.count==2 && failures==1 && !cleanup.current());revokeOnClose=false;valid=true
    require(opens==5 && closes==5 && calls==161)
    let wide=transport(withAudio:true,rate:48000)
    for _ in 0..<500{feed(wide,count:480,rate:48000)}
    require(events.count==3 && events[2].result == .noSpeech && events[2].totalSamples==80000)
    require(asrOpens==0 && ownedAudio?.retainedSamples==0 && wide.retainedSamples==0)
    wide.close();worker.sync{};require(opens==6 && closes==6 && calls==318)
    try signed.activate(2);require(!signed.lease.verified())
    do{_=try signed.lease.openVad(allowed:{true},api:api);exit(2)}catch{}
    require(opens==6 && closes==6)
    print("{\"scope\":\"IOS_SIMULATOR_CAPTURE_TRANSPORT\",\"synthetic\":true,\"quiet_valid_samples\":80000,\"eof_valid_samples\":7,\"native_calls\":318,\"opens\":6,\"closes\":6,\"wide_source_samples\":240000,\"wide_normalized_samples\":80000,\"separate_worker_verified\":true,\"signed_vad_pack_checked\":true,\"signed_epoch_revocation_rejected\":true,\"quiet_asr_opens\":0,\"quiet_owned_audio_cleared\":true,\"stop_during_inference_rejected\":true,\"stop_without_new_frames_closed\":true,\"cleanup_revocation_rejected\":true,\"physical\":\"NOT_RUN\"}")
  }
}
