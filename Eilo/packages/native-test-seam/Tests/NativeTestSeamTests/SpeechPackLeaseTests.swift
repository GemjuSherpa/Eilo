import Foundation
import CryptoKit
import XCTest
@testable import NativeTestSeam

final class SpeechPackLeaseTests:XCTestCase {
  final class Fixture {
    let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString),key=P256.Signing.PrivateKey()
    let runtime=String(repeating:"a",count:40),evidence=String(repeating:"c",count:64)
    let names=Array(SpeechPackSelection.asrNames).sorted()+["silero.onnx"]
    var sources=[URL](),pins=[SpeechArtifactPin]()
    var store:PackStore!
    init()throws {
      try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true)
      store=PackStore(root:root.appendingPathComponent("store"),trust:["test-key":key.publicKey.derRepresentation],runtime:runtime,licenseEvidence:[evidence])
      for (i,name) in names.enumerated(){let file=root.appendingPathComponent(name);try Data([UInt8(i),2,3,4]).write(to:file);sources.append(file)
        pins.append(try SpeechArtifactPin(id:"asset-\(i)",filename:name,sha256:Self.digest(file),bytes:4,licenseEvidence:evidence))}
    }
    static func digest(_ file:URL)throws->String{SHA256.hash(data:try Data(contentsOf:file)).map{String(format:"%02x",$0)}.joined()}
    func selection(_ kind:SpeechPackKind,pins override:[SpeechArtifactPin]?=nil,pack:String="test-pack",runtime rr:String?=nil)throws->SpeechPackSelection {
      try SpeechPackSelection(packID:pack,runtimeRevision:rr ?? runtime,kind:kind,pins:override ?? (kind == .vad ? [pins.last!]:Array(pins.dropLast())))
    }
    func activate(_ revision:Int=1,wrongRole:Bool=false,wrongLicense:Bool=false,wrongAsrRole:Bool=false)throws {
      let artifacts=pins.reversed().map{pin->[String:Any]in
        let vad=pin.filename=="silero.onnx"
        return ["id":pin.id,"filename":pin.filename,"role":vad ? (wrongRole ? "asr":"vad"):(pin.filename=="tokenizer.bin" ? "tokenizer":(wrongAsrRole && pin.filename=="streaming_config.json" ? "wake":"asr")),"url":"https://models.example.test/"+pin.filename,"sha256":pin.sha256,"bytes":pin.bytes,"license":wrongLicense ? "Apache-2.0":"MIT","licenseEvidence":evidence]
      }
      let data=try JSONSerialization.data(withJSONObject:["schema":1,"packId":"test-pack","revision":revision,"runtimeRevision":runtime,"minAndroid":35,"minIos":18,"artifacts":artifacts],options:[.sortedKeys,.withoutEscapingSlashes])
      let pack=try VerifiedPack.verify(payload:data,signature:key.signature(for:data).derRepresentation,keyID:"test-key",algorithm:"ES256",trust:["test-key":key.publicKey.derRepresentation],runtime:runtime)
      try store.activate(pack,proofs:pack.manifest.artifacts.enumerated().map{try VerifiedArtifact.verify(pack,index:$0.offset,file:sources[names.firstIndex(of:$0.element.filename)!])},cancel:PackCancellation())
    }
    func lease(_ kind:SpeechPackKind)throws->SpeechPackLease{try SpeechPackLease.resolve(store:store,selection:selection(kind))}
    deinit{try? FileManager.default.removeItem(at:root)}
  }
  func testSignedShuffledExactVadAndAllAsrFilesResolve()throws {
    let f=try Fixture();try f.activate();let vad=try f.lease(.vad),asr=try f.lease(.asr)
    var vadCloses=0,asrCloses=0
    let v=try vad.openVad(allowed:{true},api:NativeVadAPI(create:{path in XCTAssertTrue(path.hasSuffix("/silero.onnx"));return OpaquePointer(bitPattern:1)},process:{_,p,final in NativeVadObservation(probability:0.1,startSample:0,samples:p.count,final:final)},destroy:{_ in vadCloses+=1}))
    _=try [Float](repeating:0,count:512).withUnsafeBufferPointer{try v.process($0,final:true)}
    let a=try asr.openAsr(allowed:{true},api:NativeAsrAPI(create:{directory in for name in SpeechPackSelection.asrNames{XCTAssertTrue(FileManager.default.fileExists(atPath:directory+"/"+name))};return OpaquePointer(bitPattern:2)},accept:{_,_ in 0},text:{_,_,out in out[0]=65;out[1]=0;return 0},destroy:{_ in asrCloses+=1}))
    XCTAssertEqual(try a.text(finish:true),"A");a.close();XCTAssertEqual(vadCloses,1);XCTAssertEqual(asrCloses,1)
    XCTAssertThrowsError(try vad.openAsr(allowed:{true}));XCTAssertThrowsError(try asr.openVad(allowed:{true}))
    vad.close();asr.close();XCTAssertFalse(vad.verified());XCTAssertFalse(asr.verified())
  }
  func testExactPinPackRuntimeSizeHashAndLicenseEvidenceRequired()throws {
    let f=try Fixture();try f.activate();let pin=f.pins.last!
    XCTAssertThrowsError(try SpeechArtifactPin(id:"bad\n",filename:pin.filename,sha256:pin.sha256,bytes:4,licenseEvidence:f.evidence))
    for bad in [try SpeechArtifactPin(id:"missing",filename:pin.filename,sha256:pin.sha256,bytes:4,licenseEvidence:f.evidence),try SpeechArtifactPin(id:pin.id,filename:pin.filename,sha256:String(repeating:"d",count:64),bytes:4,licenseEvidence:f.evidence),try SpeechArtifactPin(id:pin.id,filename:pin.filename,sha256:pin.sha256,bytes:5,licenseEvidence:f.evidence),try SpeechArtifactPin(id:pin.id,filename:pin.filename,sha256:pin.sha256,bytes:4,licenseEvidence:String(repeating:"d",count:64))] {
      XCTAssertThrowsError(try SpeechPackLease.resolve(store:f.store,selection:f.selection(.vad,pins:[bad])))
    }
    XCTAssertThrowsError(try SpeechPackLease.resolve(store:f.store,selection:f.selection(.asr,pack:"other")))
    XCTAssertThrowsError(try SpeechPackLease.resolve(store:f.store,selection:f.selection(.asr,runtime:String(repeating:"b",count:40))))
    XCTAssertThrowsError(try f.selection(.asr,pins:Array(f.pins.dropLast(2))))
    XCTAssertThrowsError(try f.selection(.vad,pins:[pin,pin]))
  }
  func testUntrustedUnlicensedMissingAndCorruptStoreDenied()throws {
    let f=try Fixture();XCTAssertThrowsError(try f.lease(.asr));try f.activate()
    for store in [PackStore(root:f.root.appendingPathComponent("store"),trust:[:],runtime:f.runtime,licenseEvidence:[f.evidence]),PackStore(root:f.root.appendingPathComponent("store"),trust:["test-key":f.key.publicKey.derRepresentation],runtime:f.runtime)] {
      XCTAssertThrowsError(try SpeechPackLease.resolve(store:store,selection:f.selection(.asr)))
    }
    let snapshot=try f.store.verifiedFiles()!;try Data([9]).write(to:snapshot.1[0]);XCTAssertThrowsError(try f.lease(.asr))
  }
  func testSignedWrongRoleOrLicenseStillDenied()throws {
    for wrongRole in [false,true]{let f=try Fixture();try f.activate(wrongRole:wrongRole,wrongLicense:!wrongRole);XCTAssertThrowsError(try f.lease(.vad));if !wrongRole{XCTAssertThrowsError(try f.lease(.asr))}}
    let f=try Fixture();try f.activate(wrongAsrRole:true);XCTAssertThrowsError(try f.lease(.asr))
  }
  func testSameFilesNewEpochAndExplicitCloseNeverReviveLease()throws {
    let f=try Fixture();try f.activate();let old=try f.lease(.asr);try f.activate(2)
    XCTAssertFalse(old.verified());XCTAssertThrowsError(try old.openAsr(allowed:{true}))
    let fresh=try f.lease(.asr);XCTAssertTrue(fresh.verified());fresh.close();XCTAssertFalse(fresh.verified())
  }
  func testRevocationDuringCreationAndProcessingClosesNativeStream()throws {
    for duringCreate in [false,true]{let f=try Fixture();try f.activate();let lease=try f.lease(.vad);var closes=0
      let api=NativeVadAPI(create:{_ in if duringCreate{lease.close()};return OpaquePointer(bitPattern:1)},process:{_,pcm,final in lease.close();return NativeVadObservation(probability:0.1,startSample:0,samples:pcm.count,final:final)},destroy:{_ in closes+=1})
      if duringCreate{XCTAssertThrowsError(try lease.openVad(allowed:{true},api:api))}else{let v=try lease.openVad(allowed:{true},api:api);XCTAssertThrowsError(try [Float](repeating:0,count:512).withUnsafeBufferPointer{try v.process($0,final:false)})}
      XCTAssertEqual(closes,1)
    }
  }
  func testAsrRevocationDuringFinalAndDeniedCapabilityDoNotReleaseText()throws {
    let f=try Fixture();try f.activate();let lease=try f.lease(.asr);var creates=0,closes=0
    let api=NativeAsrAPI(create:{_ in creates+=1;return OpaquePointer(bitPattern:1)},accept:{_,_ in 0},text:{_,_,out in lease.close();out[0]=65;out[1]=0;return 0},destroy:{_ in closes+=1})
    XCTAssertThrowsError(try lease.openAsr(allowed:{false},api:api));XCTAssertEqual(creates,0)
    let stream=try lease.openAsr(allowed:{true},api:api);XCTAssertThrowsError(try stream.text(finish:true));XCTAssertEqual(closes,1)
    stream.close();XCTAssertEqual(closes,1)
  }
}
