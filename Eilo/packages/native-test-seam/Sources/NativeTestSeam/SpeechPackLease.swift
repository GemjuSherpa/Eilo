import Foundation

enum SpeechPackFailure:Error {case unavailable}
enum SpeechPackKind {case vad,asr}
struct SpeechArtifactPin {
  let id,filename,sha256,licenseEvidence:String
  let bytes:Int64
  init(id:String,filename:String,sha256:String,bytes:Int64,licenseEvidence:String)throws {
    func matches(_ text:String,_ pattern:String)->Bool{text.range(of:"^(?:"+pattern+")$",options:.regularExpression) == text.startIndex..<text.endIndex}
    guard matches(id,"[a-z0-9][a-z0-9-]{0,63}"),matches(sha256,"[a-f0-9]{64}"),matches(licenseEvidence,"[a-f0-9]{64}"),
      (1...8_000_000_000).contains(bytes),PackManifest.validFilename(filename,role:"asr") || PackManifest.validFilename(filename,role:"tokenizer") else{throw SpeechPackFailure.unavailable}
    self.id=id;self.filename=filename;self.sha256=sha256;self.bytes=bytes;self.licenseEvidence=licenseEvidence
  }
}
/// Reviewed native pins, never inferred from a signed manifest's order or supplied through JS.
struct SpeechPackSelection {
  static let asrNames:Set<String>=["adapter.ort","cross_kv.ort","decoder_kv.ort","encoder.ort","frontend.model.ort","frontend.weights.ort","streaming_config.json","tokenizer.bin"]
  let packID,runtimeRevision:String
  let kind:SpeechPackKind,pins:[SpeechArtifactPin]
  init(packID:String,runtimeRevision:String,kind:SpeechPackKind,pins:[SpeechArtifactPin])throws {
    guard packID.range(of:"^[a-z0-9][a-z0-9-]{0,63}$",options:.regularExpression) == packID.startIndex..<packID.endIndex,
      runtimeRevision.range(of:"^[a-f0-9]{40}$",options:.regularExpression) == runtimeRevision.startIndex..<runtimeRevision.endIndex,
      Set(pins.map(\.id)).count==pins.count,Set(pins.map(\.filename)).count==pins.count else{throw SpeechPackFailure.unavailable}
    switch kind {
    case .vad:guard pins.count==1,pins[0].filename.hasSuffix(".onnx") else{throw SpeechPackFailure.unavailable}
    case .asr:guard Set(pins.map(\.filename))==Self.asrNames else{throw SpeechPackFailure.unavailable}
    }
    self.packID=packID;self.runtimeRevision=runtimeRevision;self.kind=kind;self.pins=pins
  }
}

/// Resolve on one installer/inference worker. Borrow checks are disk-free and epoch-revocable.
/// App-private slots must remain immutable; revoke before maintenance. Stream close stays with
/// its worker owner. Lease close does not join or destroy a concurrently borrowed native handle.
final class SpeechPackLease {
  private let store:PackStore,epoch:UUID,kind:SpeechPackKind,paths:[URL]
  private let lock=NSLock()
  private var active=true
  private init(store:PackStore,epoch:UUID,kind:SpeechPackKind,paths:[URL]){self.store=store;self.epoch=epoch;self.kind=kind;self.paths=paths}
  func verified()->Bool{lock.lock();let valid=active;lock.unlock();return valid && store.epoch==epoch}
  func close(){lock.lock();active=false;lock.unlock()}
  static func resolve(store:PackStore,selection:SpeechPackSelection)throws->SpeechPackLease {
    do {
      let epoch=store.epoch
      guard let snapshot=try store.verifiedFiles(),snapshot.0.manifest.packID==selection.packID,
        snapshot.0.manifest.runtimeRevision==selection.runtimeRevision else{throw SpeechPackFailure.unavailable}
      let manifest=snapshot.0.manifest
      let paths=try selection.pins.map{pin->URL in
        guard let index=manifest.artifacts.firstIndex(where:{$0.id==pin.id})else{throw SpeechPackFailure.unavailable}
        let artifact=manifest.artifacts[index]
        let role=selection.kind == .vad ? "vad":(pin.filename=="tokenizer.bin" ? "tokenizer":"asr")
        guard artifact.filename==pin.filename,artifact.role==role,artifact.sha256==pin.sha256,artifact.bytes==pin.bytes,
          artifact.license=="MIT",artifact.licenseEvidence==pin.licenseEvidence else{throw SpeechPackFailure.unavailable}
        return snapshot.1[index]
      }
      guard store.epoch==epoch,!paths.isEmpty,Set(paths.map{$0.deletingLastPathComponent()}).count==1 else{throw SpeechPackFailure.unavailable}
      return SpeechPackLease(store:store,epoch:epoch,kind:selection.kind,paths:paths)
    }catch{throw SpeechPackFailure.unavailable}
  }
  func openVad(allowed:@escaping ()->Bool,api:NativeVadAPI = .linked)throws->NativeVadStream {
    guard kind == .vad,verified(),allowed()else{throw VadFailure.unavailable}
    return try NativeVadStream(model:paths[0].path,verified:{self.verified() && allowed()},api:api)
  }
  func openAsr(allowed:@escaping ()->Bool,api:NativeAsrAPI = .linked)throws->NativeAsrStream {
    guard kind == .asr,verified(),allowed()else{throw AsrFailure.unavailable}
    return try NativeAsrStream(directory:paths[0].deletingLastPathComponent().path,verified:{self.verified() && allowed()},api:api)
  }
}
