import Foundation
import CryptoKit

private struct InstallerPermission:MicrophonePermissionAdapter {
  func status()->MicrophonePermission{.granted}
  func request(_ completion:@escaping(MicrophonePermission)->Void){completion(.granted)}
}
private struct InstallerModels:ModelReadinessAdapter{func status()->ModelStatus{.ready}}
private final class InstallerEffects:ControllerEffects {
  func startCapture()throws->Bool{true}
  func releaseCapture()throws{}
  func cancelWork()throws{}
  func clearVolatileContext()throws{}
  func playClause(_ clause:String)throws{}
}
/// Ephemeral ES256 lab pack. Pins arrive only from the verified offline runner, never JS.
private final class InstallerPack {
  let store:PackStore,vad:SpeechPackSelection,asr:SpeechPackSelection
  let key=P256.Signing.PrivateKey(),runtime=String(repeating:"a",count:40),evidence=String(repeating:"c",count:64)
  let pins:[SpeechArtifactPin],sources:[URL]
  init(root:URL,manifest:URL)throws {
    let rows=try JSONSerialization.jsonObject(with:Data(contentsOf:manifest)) as! [[String:Any]]
    let license=String(repeating:"c",count:64)
    pins=try rows.map{try SpeechArtifactPin(id:$0["id"] as! String,filename:$0["filename"] as! String,
      sha256:$0["sha256"] as! String,bytes:($0["bytes"] as! NSNumber).int64Value,licenseEvidence:license)}
    sources=rows.map{URL(fileURLWithPath:$0["source"] as! String)}
    store=PackStore(root:root,trust:["lab-key":key.publicKey.derRepresentation],runtime:runtime,licenseEvidence:[evidence])
    vad=try SpeechPackSelection(packID:"lab-speech",runtimeRevision:runtime,kind:.vad,pins:pins.filter{$0.id=="vad"})
    asr=try SpeechPackSelection(packID:"lab-speech",runtimeRevision:runtime,kind:.asr,pins:pins.filter{$0.id != "vad"})
    try activate(1)
  }
  func activate(_ revision:Int)throws {
    let artifacts=pins.map{p->[String:Any] in ["id":p.id,"filename":p.filename,
      "role":p.id=="vad" ? "vad":(p.filename=="tokenizer.bin" ? "tokenizer":"asr"),
      "url":"https://models.example.test/"+p.filename,"sha256":p.sha256,"bytes":p.bytes,"license":"MIT","licenseEvidence":evidence]}
    let data=try JSONSerialization.data(withJSONObject:["schema":1,"packId":"lab-speech","revision":revision,
      "runtimeRevision":runtime,"minAndroid":35,"minIos":18,"artifacts":artifacts],options:[.sortedKeys,.withoutEscapingSlashes])
    let verified=try VerifiedPack.verify(payload:data,signature:key.signature(for:data).derRepresentation,keyID:"lab-key",algorithm:"ES256",
      trust:["lab-key":key.publicKey.derRepresentation],runtime:runtime)
    let proofs=try pins.indices.map{try VerifiedArtifact.verify(verified,index:$0,file:sources[$0])}
    try store.activate(verified,proofs:proofs,cancel:PackCancellation())
  }
}
@main struct SpeechInstallerProbe {
  static func require(_ value:Bool,line:UInt=#line){if !value{fputs("installer assertion line \(line)\n",stderr);exit(2)}}
  static func main()throws {
    require(CommandLine.arguments.count==3)
    let raw=try Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2]))
    require(raw.count%4==0 && raw.count>0 && raw.count<=480000*4)
    var input=raw.withUnsafeBytes{buffer in stride(from:0,to:raw.count,by:4).map{Float(bitPattern:UInt32(littleEndian:buffer.loadUnaligned(fromByteOffset:$0,as:UInt32.self)))}}
    defer{input.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
    require(input.allSatisfy{$0.isFinite && (-1...1).contains($0)})
    let storeRoot=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    defer{try? FileManager.default.removeItem(at:storeRoot)}
    let pack=try InstallerPack(root:storeRoot,manifest:URL(fileURLWithPath:CommandLine.arguments[1]))
    let worker=DispatchQueue(label:"eilo.signed.installer.evaluation"),specific=DispatchSpecificKey<Bool>()
    worker.setSpecific(key:specific,value:true)
    let vbase=NativeVadAPI.linked,abase=NativeAsrAPI.linked
    var results=[[String:Any]]()
    for phase in ["speech16","speech48","quiet","stop-final","replace-final","idle-stop","stale-ticket","corrupt-pack"] {
      let effects=InstallerEffects()
      // Exact effects identity must match the controller, even in the lab.
      let c=NativeController(effects:effects,permission:InstallerPermission(),models:InstallerModels())
      require(c.dispatch(.start));require(c.dispatch(.speechDetected,token:c.token))
      let token=c.token!,rate=phase=="speech48" ? 48000:16000,slot=VadCaptureSlot(sampleRate:rate)
      var vo=0,vc=0,ao=0,ac=0,vadCalls=0,asrCalls=0,finals=0,texts=0,metadata=0
      var textDigest="",outcome:VadCaptureOutcome?
      let va=NativeVadAPI(create:{p in require(DispatchQueue.getSpecific(key:specific)==true);let h=vbase.create(p);if h != nil{vo+=1};return h},
        process:{h,p,f in require(DispatchQueue.getSpecific(key:specific)==true);vadCalls+=1;return vbase.process(h,p,f)},
        destroy:{h in require(DispatchQueue.getSpecific(key:specific)==true);vc+=1;vbase.destroy(h)})
      let aa=NativeAsrAPI(create:{p in require(DispatchQueue.getSpecific(key:specific)==true);let h=abase.create(p);if h != nil{ao+=1};return h},
        accept:{h,p in require(DispatchQueue.getSpecific(key:specific)==true);asrCalls+=1;return abase.accept(h,p)},
        text:{h,final,buffer in
          require(DispatchQueue.getSpecific(key:specific)==true);let status=abase.text(h,final,buffer)
          if final{finals+=1;if phase=="stop-final"{_ = c.stop()};if phase=="replace-final"{do{try pack.activate(2)}catch{exit(2)}}}
          return status
        },destroy:{h in require(DispatchQueue.getSpecific(key:specific)==true);ac+=1;abase.destroy(h)})
      let ticket=slot.prepare(capture:effects,controller:c,token:token)!
      if phase=="stale-ticket"{slot.detach()}
      if phase=="corrupt-pack" {
        let files=try pack.store.verifiedFiles()!;try Data([0]).write(to:files.1.last!)
      }
      let installed=worker.sync{SpeechCaptureInstaller.install(ticket:ticket,vadStore:pack.store,vadSelection:pack.vad,
        asrStore:pack.store,asrSelection:pack.asr,schedule:{worker.async(execute:$0)},vadAPI:va,asrAPI:aa,
        accepted:{value in metadata+=1;outcome=value},recognized:{text in
          require(!text.text.isEmpty);texts+=1;textDigest=SHA256.hash(data:Data(text.text.utf8)).map{String(format:"%02x",$0)}.joined()
        })}
      if phase=="stale-ticket" || phase=="corrupt-pack"{require(!installed && vo==0 && ao==0)}else {
        require(installed)
        var pcm=phase=="quiet" || phase=="idle-stop" ? [Float](repeating:0,count:phase=="quiet" ? 80000:512):input+[Float](repeating:0,count:32000)
        if rate==48000{pcm=pcm.flatMap{[$0,$0,$0]}}
        var offset=0
        while offset<pcm.count {
          let end=min(offset+(rate==48000 ? 960:320),pcm.count)
          pcm.withUnsafeBufferPointer{slot.submit(UnsafeBufferPointer(rebasing:$0[offset..<end]),sampleRate:rate)}
          worker.sync{};offset=end
        }
        if phase=="idle-stop"{_ = c.stop()}else{slot.finish()}
        worker.sync{};pcm.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}
        if phase=="speech16" || phase=="speech48"{require(texts==1 && metadata==1 && ao==1 && finals==1 && outcome?.result == .complete)}
        else if phase=="quiet"{require(ao==0 && texts==0 && metadata==1 && outcome?.result == .noSpeech)}
        else if phase=="idle-stop"{require(vo==1 && ao==0 && texts==0 && metadata==0)}
        else{require(ao==1 && finals==1 && texts==0 && metadata==0)}
      }
      slot.close();worker.sync{};require(vo==vc && ao==ac)
      results.append(["case":phase,"installed":installed,"vad_opens":vo,"vad_closes":vc,"vad_calls":vadCalls,
        "asr_opens":ao,"asr_closes":ac,"asr_accept_calls":asrCalls,"asr_finals":finals,"recognized":texts,
        "metadata":metadata,"transcript_sha256":textDigest,"source_rate":rate,"normalized_samples":outcome?.totalSamples ?? 0])
    }
    let report:[String:Any]=["scope":"IOS_SIMULATOR_SIGNED_SPEECH_INSTALLER","synthetic":true,"cases":results,
      "worker_verified":true,"physical":"NOT_RUN","production":"NOT_ENABLED","lab_signing":"EPHEMERAL_ES256"]
    print(String(data:try JSONSerialization.data(withJSONObject:report,options:[.sortedKeys]),encoding:.utf8)!)
  }
}
