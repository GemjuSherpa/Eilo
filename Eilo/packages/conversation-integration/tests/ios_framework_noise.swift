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
@main struct FrameworkNoiseProbe {
  final class Counts {var opens=0,closes=0,finals=0}
  static func check(_ value:Bool){if !value{fputs("noise evaluator invariant failed\n",stderr);exit(2)}}
  static func main()throws {
    check(CommandLine.arguments.count==3)
    let root=FileManager.default.temporaryDirectory.appendingPathComponent("eilo-noise-"+UUID().uuidString)
    defer{try? FileManager.default.removeItem(at:root)}
    let pack=try InstallerPack(root:root,manifest:URL(fileURLWithPath:CommandLine.arguments[1]))
    let rows=try JSONSerialization.jsonObject(with:Data(contentsOf:URL(fileURLWithPath:CommandLine.arguments[2]))) as! [[String:Any]]
    check(rows.count==19)
    let worker=DispatchQueue(label:"eilo.noise.pairs"),key=DispatchSpecificKey<Bool>();worker.setSpecific(key:key,value:true)
    let base=NativeAsrAPI.linked,vbase=NativeVadAPI.linked
    func api(_ count:Counts)->NativeAsrAPI {
      NativeAsrAPI(create:{p in check(DispatchQueue.getSpecific(key:key)==true);let h=base.create(p);if h != nil{count.opens+=1};return h},
        accept:{h,p in check(DispatchQueue.getSpecific(key:key)==true);return base.accept(h,p)},
        text:{h,f,b in check(DispatchQueue.getSpecific(key:key)==true);if f{count.finals+=1};return base.text(h,f,b)},
        destroy:{h in check(DispatchQueue.getSpecific(key:key)==true);count.closes+=1;base.destroy(h)})
    }
    var results=[[String:Any]]()
    for row in rows {
      let raw=try Data(contentsOf:URL(fileURLWithPath:row["path"] as! String))
      let digest=SHA256.hash(data:raw).map{String(format:"%02x",$0)}.joined()
      check(digest==row["sha256"] as! String && raw.count%4==0 && (80000*4...480000*4).contains(raw.count))
      var pcm=raw.withUnsafeBytes{b in stride(from:0,to:raw.count,by:4).map{Float(bitPattern:UInt32(littleEndian:b.loadUnaligned(fromByteOffset:$0,as:UInt32.self)))}}
      defer{pcm.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
      check(pcm.allSatisfy{$0.isFinite && (-1...1).contains($0)})
      let direct=Counts(),effects=InstallerEffects(),c=NativeController(effects:InstallerEffects(),permission:InstallerPermission(),models:InstallerModels())
      check(c.dispatch(.start));check(c.dispatch(.speechDetected,token:c.token));let token=c.token!
      var available=false,nonempty=false
      try worker.sync {
        let lease=try SpeechPackLease.resolve(store:pack.store,selection:pack.asr);defer{lease.close()}
        let adapter=api(direct),stream=StreamingAsr(token,allowed:{c.recognitionAllowed(token)},open:{try lease.openAsr(allowed:{c.recognitionAllowed(token)},api:adapter)})
        defer{stream.close()}
        var ok=true
        for offset in stride(from:0,to:pcm.count,by:1600){if !pcm.withUnsafeBufferPointer({stream.accept(UnsafeBufferPointer(rebasing:$0[offset..<min(offset+1600,pcm.count)]))}){ok=false;break}}
        if ok,let final=stream.poll(finish:true){available=true;nonempty = !final.text.isEmpty}
      }
      c.stop();check(direct.opens==1 && direct.closes==1 && direct.finals==1)
      let joined=Counts(),controller=NativeController(effects:effects,permission:InstallerPermission(),models:InstallerModels())
      check(controller.dispatch(.start));check(controller.dispatch(.speechDetected,token:controller.token))
      let slot=VadCaptureSlot(sampleRate:16000),ticket=slot.prepare(capture:effects,controller:controller,token:controller.token!)!
      var metadata=0,recognized=0,joinedNonempty=false,outcome:VadCaptureOutcome?,vo=0,vc=0
      let vad=NativeVadAPI(create:{p in check(DispatchQueue.getSpecific(key:key)==true);let h=vbase.create(p);if h != nil{vo+=1};return h},
        process:{h,p,f in check(DispatchQueue.getSpecific(key:key)==true);return vbase.process(h,p,f)},
        destroy:{h in check(DispatchQueue.getSpecific(key:key)==true);vc+=1;vbase.destroy(h)})
      let installed=worker.sync{SpeechCaptureInstaller.install(ticket:ticket,vadStore:pack.store,vadSelection:pack.vad,asrStore:pack.store,asrSelection:pack.asr,
        schedule:{worker.async(execute:$0)},vadAPI:vad,asrAPI:api(joined),accepted:{metadata+=1;outcome=$0},recognized:{recognized+=1;joinedNonempty = !$0.text.isEmpty})}
      check(installed)
      for offset in stride(from:0,to:pcm.count,by:320){pcm.withUnsafeBufferPointer{slot.submit(UnsafeBufferPointer(rebasing:$0[offset..<min(offset+320,pcm.count)]),sampleRate:16000)};worker.sync{}}
      slot.finish();worker.sync{};slot.close();worker.sync{};controller.stop()
      check(vo==1 && vc==1 && joined.opens==joined.closes && joined.opens<=1 && metadata<=1 && recognized<=1)
      if row["group"] as! String == "positive_question"{check(available && nonempty && metadata==1 && recognized==1 && joinedNonempty && outcome?.result == .complete)}
      results.append(["group":row["group"]!,"input_sha256":digest,"input_samples":pcm.count,
        "direct_available":available,"direct_nonempty":nonempty,"direct_opens":direct.opens,"direct_closes":direct.closes,"direct_finals":direct.finals,
        "vad_opens":vo,"vad_closes":vc,"joined_opens":joined.opens,"joined_closes":joined.closes,"joined_finals":joined.finals,
        "metadata":metadata,"recognized":recognized,"joined_nonempty":joinedNonempty,"outcome":outcome.map{String(describing:$0.result)} ?? "unavailable","consumed_samples":outcome?.totalSamples ?? 0])
    }
    try FileManager.default.removeItem(at:root)
    let result:[String:Any]=["cases":results,"temporary_pack_removed":!FileManager.default.fileExists(atPath:root.path),"worker_verified":true]
    print("EILO_NOISE_RESULT\t"+String(decoding:try JSONSerialization.data(withJSONObject:result,options:[.sortedKeys]),as:UTF8.self))
  }
}
