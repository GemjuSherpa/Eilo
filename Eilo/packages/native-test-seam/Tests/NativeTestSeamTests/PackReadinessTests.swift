import Foundation
import XCTest
@testable import NativeTestSeam
final class MutableModels: ModelReadinessAdapter { var value: ModelStatus = .ready;func status() -> ModelStatus { value } }
final class PackReadinessTests: XCTestCase {
 func testEveryMissingUnsupportedReasonPreventsPromptAndCapture() {
  for status in ModelStatus.allCases.filter({ $0 != .ready }) {
   let spy=EffectsSpy(),p=FakePermission(.notRequested),models=MutableModels();models.value=status
   let c=NativeController(effects:spy,permission:p,models:models);XCTAssertFalse(c.dispatch(.start));XCTAssertEqual(spy.started,0);XCTAssertEqual(p.requests,0);XCTAssertEqual(c.state,.setup);XCTAssertEqual(c.snapshot()["modelStatus"] as? String,status.rawValue)
  }
 }
 func testModelLossDuringPromptAndCaptureCannotStartOrPublish() {
  let spy=EffectsSpy(),p=FakePermission(.notRequested),models=MutableModels(),c=NativeController(effects:spy,permission:p,models:models)
  c.dispatch(.start);models.value = .corrupt;p.complete(.granted);XCTAssertEqual(spy.started,0)
  models.value = .ready;c.modelsChanged();XCTAssertEqual(spy.started,0);spy.onStart={ models.value = .missing };XCTAssertFalse(c.dispatch(.start));XCTAssertNil(c.token)
  spy.onStart=nil;models.value = .ready;c.modelsChanged();c.dispatch(.start);c.dispatch(.speechDetected,token:c.token);c.dispatch(.endpoint,token:c.token);let old=c.token!;models.value = .missing;XCTAssertFalse(c.releaseSpeech(old,clause:"synthetic"));XCTAssertTrue(spy.clauses.isEmpty)
 }
 func testSignedLlmAloneCannotClaimCompletePipeline() throws {
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString);try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true);defer { try? FileManager.default.removeItem(at:root) }
  let (p,trust)=try PackFixtures.signed(),s=PackStore(root:root.appendingPathComponent("store"),trust:trust,runtime:PackFixtures.runtime,licenseEvidence:[String(repeating:"c",count:64)]),gate=PackReadiness(store:s)
  XCTAssertEqual(gate.refresh(),.unsupported);XCTAssertEqual(gate.refresh(configurationSupported:true,offlineVoice:true),.missing)
  let f=root.appendingPathComponent("part");try Data([1,2,3,4]).write(to:f);try s.activate(p,proofs:[VerifiedArtifact.verify(p,index:0,file:f)],cancel:PackCancellation());XCTAssertEqual(gate.refresh(configurationSupported:true,offlineVoice:true),.incomplete)
  try Data([9,9,9,9]).write(to:s.file(p,index:0));XCTAssertEqual(gate.refresh(configurationSupported:true,offlineVoice:true),.corrupt)
 }
 func testCompletePackRequiresOfflineVoiceAndActivationInvalidatesCachedReady() throws {
  let root=FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString);try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true);defer { try? FileManager.default.removeItem(at:root) }
  var o=try JSONSerialization.jsonObject(with:PackFixtures.payload) as! [String:Any];let base=(o["artifacts"] as! [[String:Any]])[0]
  o["artifacts"]=["llm","asr","wake","vad"].map { role -> [String:Any] in var f=base;f["id"]=role;f["role"]=role;f["filename"]=role+".onnx";return f }
  let (p,trust)=try PackFixtures.signed(JSONSerialization.data(withJSONObject:o,options:.withoutEscapingSlashes)),store=PackStore(root:root.appendingPathComponent("store"),trust:trust,runtime:PackFixtures.runtime,licenseEvidence:[String(repeating:"c",count:64)])
  let f=root.appendingPathComponent("part");try Data([1,2,3,4]).write(to:f);let proofs=try p.manifest.artifacts.indices.map { try VerifiedArtifact.verify(p,index:$0,file:f) };try store.activate(p,proofs:proofs,cancel:PackCancellation())
  let gate=PackReadiness(store:store);XCTAssertEqual(gate.refresh(configurationSupported:true,offlineVoice:false),.offlineVoiceMissing);XCTAssertEqual(gate.refresh(configurationSupported:true,offlineVoice:true),.ready)
  try store.activate(p,proofs:proofs,cancel:PackCancellation());XCTAssertEqual(gate.status(),.missing);XCTAssertEqual(gate.refresh(configurationSupported:true,offlineVoice:true),.ready)
  let incompatible=PackReadiness(store:PackStore(root:root.appendingPathComponent("store"),trust:trust,runtime:String(repeating:"d",count:40),licenseEvidence:[String(repeating:"c",count:64)]));XCTAssertEqual(incompatible.refresh(configurationSupported:true,offlineVoice:true),.incompatible)
 }

}
