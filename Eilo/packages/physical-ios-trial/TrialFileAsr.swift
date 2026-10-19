import Foundation
import CryptoKit

enum TrialFileAsr {
  static let fixtureDigest="5f310e91b7cb36d33ab09252cc44f1dd045178cb172e65827a98eebe9ca78102"
  private struct Manifest:Decodable{struct Item:Decodable{let id,reference:String;let samples:Int};let cases:[Item]}
  private struct Pin:Decodable{let id,sha256:String;let samples:Int}
  static func run(assets:URL,store:PackStore,selection:SpeechPackSelection,allowed:@escaping()->Bool)throws->[[String:Any]]{
    let data=try Data(contentsOf:assets.appendingPathComponent("asr-fixtures.json"))
    guard allowed(),SHA256.hash(data:data).map({String(format:"%02x",$0)}).joined()==fixtureDigest else{throw AsrFailure.unavailable}
    let cases=try JSONDecoder().decode(Manifest.self,from:data).cases
    let pins=try JSONDecoder().decode([Pin].self,from:Data(contentsOf:assets.appendingPathComponent("asr-pcm-pins.json")))
    guard cases.map({$0.id})==["question","name","numbers","quiet","pause","noise"],pins.map({$0.id})==cases.map({$0.id}) else{throw AsrFailure.unavailable}
    let lease=try SpeechPackLease.resolve(store:store,selection:selection);defer{lease.close()}
    var rows=[[String:Any]]()
    for (fixture,pin) in zip(cases,pins){
      guard allowed(),fixture.samples==pin.samples,(1...480000).contains(pin.samples) else{throw AsrFailure.unavailable}
      let pcmData=try Data(contentsOf:assets.appendingPathComponent(fixture.id+".f32"))
      guard pcmData.count==pin.samples*4,SHA256.hash(data:pcmData).map({String(format:"%02x",$0)}).joined()==pin.sha256 else{throw AsrFailure.unavailable}
      var pcm=pcmData.withUnsafeBytes{raw in (0..<pin.samples).map{Float(bitPattern:UInt32(littleEndian:raw.loadUnaligned(fromByteOffset:$0*4,as:UInt32.self)))}}
      defer{pcm.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
      guard pcm.allSatisfy({$0.isFinite && (-1...1).contains($0)}),allowed() else{throw AsrFailure.unavailable}
      let start=ProcessInfo.processInfo.systemUptime
      let stream=try lease.openAsr(allowed:allowed);defer{stream.close()}
      for i in stride(from:0,to:pcm.count,by:320){
        guard allowed()else{throw AsrFailure.unavailable};let end=min(i+320,pcm.count)
        try pcm.withUnsafeBufferPointer{try stream.accept(UnsafeBufferPointer(rebasing:$0[i..<end]))}
      }
      let text=try stream.text(finish:true);guard allowed() else{throw AsrFailure.unavailable}
      let score=TrialAsrScore.edits(fixture.reference,text)
      var row:[String:Any]=["fixture_id":fixture.id,"pcm_sha256":pin.sha256,"samples":pin.samples,"runtime_elapsed_ms":(ProcessInfo.processInfo.systemUptime-start)*1000]
      for(k,v) in score{row[k]=v};rows.append(row)
      stream.close()
    };return rows
  }
}
