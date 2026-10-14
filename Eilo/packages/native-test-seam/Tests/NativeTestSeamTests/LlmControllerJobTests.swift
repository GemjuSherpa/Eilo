import Foundation
import CryptoKit
import XCTest
@testable import NativeTestSeam

final class LlmControllerJobTests: XCTestCase {
  final class Fixture {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    let source: URL, store: PackStore, selection: LlmPackSelection, pack: VerifiedPack
    var opens = 0, closes = 0
    var onOpen: () -> Void = {}, onClose: () -> Void = {}
    init() throws {
      source = root.appendingPathComponent("source"); try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
      try Data([1,2,3,4]).write(to: source)
      let hash = SHA256.hash(data: Data([1,2,3,4])).map { String(format: "%02x", $0) }.joined()
      let key = P256.Signing.PrivateKey(), runtime = String(repeating: "a", count: 40), evidence = String(repeating: "c", count: 64)
      let trust = ["test-key": key.publicKey.derRepresentation]
      store = PackStore(root: root.appendingPathComponent("store"), trust: trust, runtime: runtime, licenseEvidence: [evidence])
      selection = try LlmPackSelection(packID: "test-pack", runtimeRevision: runtime,
        model: LlmArtifactPin(id: "model", sha256: hash, bytes: 4, licenseEvidence: evidence))
      let payload = try JSONSerialization.data(withJSONObject: ["schema":1,"packId":"test-pack","revision":1,
        "runtimeRevision":runtime,"minAndroid":35,"minIos":18,"artifacts":[["id":"model","filename":"model.gguf","role":"llm",
        "url":"https://models.example.test/model.gguf","sha256":hash,"bytes":4,"license":"Apache-2.0","licenseEvidence":evidence]]],
        options:[.sortedKeys,.withoutEscapingSlashes])
      pack = try VerifiedPack.verify(payload: payload, signature: key.signature(for: payload).derRepresentation, keyID: "test-key", algorithm: "ES256", trust: trust, runtime: runtime)
      try activate()
    }
    func activate() throws { try store.activate(pack, proofs: [VerifiedArtifact.verify(pack, index: 0, file: source)], cancel: PackCancellation()) }
    func open(_ file: URL, _ pin: LlmArtifactPin) throws -> LlmVerifiedDescriptor {
      opens += 1; onOpen(); return LlmVerifiedDescriptor(31) { self.closes += 1; self.onClose() }
    }
    deinit { try? FileManager.default.removeItem(at: root) }
  }
  final class Backend {
    var creates = 0, destroys = 0, cancels = 0, nexts = 0, begins = 0
    var onLoad: () -> Int32 = { 0 }, onBegin: () -> Int32 = { 0 }, onNext: () -> Void = {}, onDestroy: () -> Void = {}
    var piece: UnsafeMutableBufferPointer<CChar>?
    var api: NativeLlmAPI { NativeLlmAPI(create: { self.creates += 1; return OpaquePointer(bitPattern: 7) },
      load: { _,_,_ in self.onLoad() }, begin: { _,prompt,_ in self.begins += 1; XCTAssertEqual(prompt.first, 65); return self.onBegin() },
      next: { _,out,count in self.nexts += 1; self.piece = out; if self.nexts == 1 { out[0] = 66; count = 1; self.onNext(); return 1 }; count = 0; return 0 },
      cancel: { _ in self.cancels += 1 }, destroy: { _ in self.destroys += 1; self.onDestroy() }) }
  }
  final class Queue {
    var tasks: [() -> Void] = []
    func schedule(_ work: @escaping () -> Void) { tasks.append(work) }
    func start() { Thread(block: tasks.removeFirst()).start() }
  }
  final class Effects: ControllerEffects {
    func startCapture() -> Bool { true }
    func playClause(_ clause: String) { XCTFail("raw output is not speech") }
    func cancelWork() {} ; func releaseCapture() {} ; func clearVolatileContext() {}
  }
  struct Permission: MicrophonePermissionAdapter {
    func status() -> MicrophonePermission { .granted }
    func request(_ completion: @escaping (MicrophonePermission) -> Void) { completion(.granted) }
  }
  struct Models: ModelReadinessAdapter { func status() -> ModelStatus { .ready } }
  func controller() -> NativeController {
    let c = NativeController(effects: Effects(), permission: Permission(), models: Models())
    XCTAssertTrue(c.dispatch(.start)); XCTAssertTrue(c.dispatch(.speechDetected, token:c.token)); XCTAssertTrue(c.dispatch(.endpoint, token:c.token)); return c
  }
  func prompt() throws -> LlmOwnedPrompt { try [UInt8](arrayLiteral:65).withUnsafeBufferPointer { try LlmOwnedPrompt($0) } }
  func submit(_ f: Fixture, _ c: NativeController, _ q: Queue, _ backend: Backend, _ p: LlmOwnedPrompt,
              consume: @escaping (UnsafeBufferPointer<UInt8>) throws -> Void = { _ in }) -> LlmControllerJob? {
    LlmControllerJob.submit(controller:c, token:c.token!, store:f.store, selection:f.selection, prompt:p, outputLimit:8,
      api:backend.api, open:f.open, schedule:q.schedule, consume:consume)
  }
  func testSuccessfulJobOwnsPromptAndLeavesThinking() throws {
    let f=try Fixture(), c=controller(), q=Queue(), api=Backend(), p=try prompt()
    let job=try XCTUnwrap(submit(f,c,q,api,p) { XCTAssertEqual(Array($0),[66]); XCTAssertFalse(Thread.isMainThread) })
    XCTAssertEqual(api.creates,0);q.start();XCTAssertEqual(job.awaitCompletion(timeout:5),.completed)
    XCTAssertTrue(p.cleared);XCTAssertEqual(api.destroys,1);XCTAssertEqual(f.closes,1);XCTAssertEqual(c.state,.thinking)
    XCTAssertFalse(c.snapshot().values.contains { $0 is Data })
  }
  func testQueuedStopAndAllPrivacyChangesClearPromptWithoutOpening() throws {
    for change in [PrivacyChange.lock,.unlock,.privateSession,.historySession,.identityReset,.deleteAll] {
      let f=try Fixture(), c=controller(), q=Queue(), api=Backend(), p=try prompt();let job=try XCTUnwrap(submit(f,c,q,api,p))
      c.privacyTransition(change);XCTAssertTrue(p.cleared);q.start();XCTAssertEqual(job.awaitCompletion(timeout:5),.cancelled);XCTAssertEqual(f.opens,0)
    }
    let f=try Fixture(),c=controller(),q=Queue(),api=Backend(),p=try prompt();let job=try XCTUnwrap(submit(f,c,q,api,p));c.stop();q.start()
    XCTAssertEqual(job.awaitCompletion(timeout:5),.cancelled);XCTAssertTrue(p.cleared);XCTAssertEqual(api.creates,0)
  }
  func testDuplicateForeignAndStaleTicketsRejectAndClear() throws {
    let f=try Fixture(),c=controller(),q=Queue(),api=Backend(),p=try prompt();let old=c.token!;let job=try XCTUnwrap(submit(f,c,q,api,p))
    XCTAssertNil(submit(f,c,q,api,p));XCTAssertFalse(p.cleared) // Do not erase the first job's transferred buffer.
    let duplicate=try prompt();XCTAssertNil(submit(f,c,q,api,duplicate));XCTAssertTrue(duplicate.cleared)
    let foreign=try prompt();XCTAssertNil(LlmControllerJob.submit(controller:c,token:controller().token!,store:f.store,selection:f.selection,prompt:foreign,consume:{_ in}));XCTAssertTrue(foreign.cleared)
    c.cancelGeneration();q.start();XCTAssertEqual(job.awaitCompletion(timeout:5),.cancelled)
    let stale=try prompt();XCTAssertNil(LlmControllerJob.submit(controller:c,token:old,store:f.store,selection:f.selection,prompt:stale,consume:{_ in}));XCTAssertTrue(stale.cleared)
  }
  func testStopDuringLoadAndPrefillSignalsWithoutDestroyingWorker() throws {
    for loading in [true,false] {
      let f=try Fixture(),c=controller(),q=Queue(),api=Backend(),p=try prompt();let entered=DispatchSemaphore(value:0),release=DispatchSemaphore(value:0)
      let blocking:()->Int32={ entered.signal();return release.wait(timeout:.now()+5) == .success ? 0 : -3 }
      if loading { api.onLoad=blocking } else { api.onBegin=blocking }
      let job=try XCTUnwrap(submit(f,c,q,api,p));q.start();XCTAssertEqual(entered.wait(timeout:.now()+5),.success)
      c.stop();XCTAssertGreaterThan(api.cancels,0);XCTAssertEqual(api.destroys,0);XCTAssertNil(job.awaitCompletion(timeout:0))
      XCTAssertEqual(p.cleared,loading);release.signal();XCTAssertEqual(job.awaitCompletion(timeout:5),.cancelled);XCTAssertTrue(p.cleared);XCTAssertEqual(api.destroys,1)
    }
  }
  func testStoppedDecodeCannotReleaseOrAffectRestartedTurn() throws {
    let f=try Fixture(),c=controller(),q=Queue(),api=Backend(),p=try prompt();let entered=DispatchSemaphore(value:0),release=DispatchSemaphore(value:0)
    api.onNext={entered.signal();_ = release.wait(timeout:.now()+5)}
    let job=try XCTUnwrap(submit(f,c,q,api,p,consume:{_ in XCTFail("stale output")}));q.start();XCTAssertEqual(entered.wait(timeout:.now()+5),.success)
    c.stop();XCTAssertTrue(c.dispatch(.start));XCTAssertTrue(c.dispatch(.speechDetected,token:c.token));XCTAssertTrue(c.dispatch(.endpoint,token:c.token))
    release.signal();XCTAssertEqual(job.awaitCompletion(timeout:5),.cancelled);XCTAssertEqual(c.state,.thinking)
  }
  func testPackRevocationDuringDecodeAndAtEndRejectsCompletion() throws {
    for end in [true,false] {
      let f=try Fixture(),c=controller(),q=Queue(),api=Backend(),p=try prompt()
      let revoke={try? f.activate();return ()}
      if end {api.onDestroy=revoke} else {api.onNext=revoke}
      let job=try XCTUnwrap(submit(f,c,q,api,p,consume:{_ in if !end {XCTFail("revoked piece")}}));q.start()
      XCTAssertEqual(job.awaitCompletion(timeout:5),.unavailable);XCTAssertEqual(c.error,.unavailable);XCTAssertEqual(api.destroys,1)
    }
  }
  func testInlineRejectedAndIneligibleSchedulingNeverOpensModel() throws {
    enum Failure:Error{case synthetic}
    let f=try Fixture()
    for schedule in [({work in work()}),({ _ in throw Failure.synthetic })] as [(@escaping ()->Void)throws->Void] {
      let c=controller(),p=try prompt();let job=try XCTUnwrap(LlmControllerJob.submit(controller:c,token:c.token!,store:f.store,selection:f.selection,prompt:p,schedule:schedule,consume:{_ in}))
      XCTAssertEqual(job.awaitCompletion(timeout:5),.unavailable);XCTAssertTrue(p.cleared);XCTAssertEqual(f.opens,0)
    }
    let c=controller(),q=Queue(),p=try prompt();let job=try XCTUnwrap(LlmControllerJob.submit(controller:c,token:c.token!,store:f.store,selection:f.selection,prompt:p,schedule:q.schedule,workerAllowed:{false},consume:{_ in}))
    q.start();XCTAssertEqual(job.awaitCompletion(timeout:5),.unavailable);XCTAssertEqual(f.opens,0)
  }
  func testMissingDefaultAndCloseRevocationFailClosed() throws {
    let f=try Fixture(),c=controller(),q=Queue(),p=try prompt()
    let job=try XCTUnwrap(LlmControllerJob.submit(controller:c,token:c.token!,store:f.store,selection:f.selection,prompt:p,open:f.open,schedule:q.schedule,consume:{_ in XCTFail()}))
    q.start();XCTAssertEqual(job.awaitCompletion(timeout:5),.unavailable);XCTAssertEqual(c.error,.unavailable);XCTAssertEqual(f.closes,1)
    let second=controller(),api=Backend(),p2=try prompt();f.onClose={second.stop()}
    let old=try XCTUnwrap(submit(f,second,q,api,p2));q.start();XCTAssertEqual(old.awaitCompletion(timeout:5),.cancelled);XCTAssertEqual(api.begins,0)
  }
  func testBorrowedConsumerCannotJoinAndThrowClearsPrompt() throws {
    enum Failure:Error{case synthetic}
    let f=try Fixture(),c=controller(),q=Queue(),api=Backend(),p=try prompt();var job:LlmControllerJob?
    job=submit(f,c,q,api,p){_ in XCTAssertNil(job?.awaitCompletion(timeout:0));throw Failure.synthetic}
    q.start();XCTAssertEqual(job?.awaitCompletion(timeout:5),.cancelled);XCTAssertTrue(p.cleared);XCTAssertEqual(c.state,.stopped)
  }
  func testPromptAndOutputBoundsRejectWithoutScheduling() throws {
    for data in [[UInt8](),[65,0],[UInt8](repeating:65,count:16385)] {XCTAssertThrowsError(try data.withUnsafeBufferPointer{try LlmOwnedPrompt($0)})}
    let f=try Fixture(),c=controller(),q=Queue()
    for limit in [0,257] {let p=try prompt();XCTAssertNil(LlmControllerJob.submit(controller:c,token:c.token!,store:f.store,selection:f.selection,prompt:p,outputLimit:limit,schedule:q.schedule,consume:{_ in}));XCTAssertTrue(p.cleared)}
    XCTAssertTrue(q.tasks.isEmpty)
  }
  func testReadOnlyModelActivationKeepsPermissions() throws {
    let f=try Fixture();try FileManager.default.setAttributes([.posixPermissions:0o400],ofItemAtPath:f.source.path)
    // Force a new private store so activation must copy the protected source.
    let key=P256.Signing.PrivateKey(),runtime=f.selection.runtimeRevision,evidence=f.selection.model.licenseEvidence
    let store=PackStore(root:f.root.appendingPathComponent("read-only-store"),trust:["test-key":key.publicKey.derRepresentation],runtime:runtime,licenseEvidence:[evidence])
    let pack=try VerifiedPack.verify(payload:f.pack.signedPayload,signature:key.signature(for:f.pack.signedPayload).derRepresentation,keyID:"test-key",algorithm:"ES256",trust:["test-key":key.publicKey.derRepresentation],runtime:runtime)
    try store.activate(pack,proofs:[VerifiedArtifact.verify(pack,index:0,file:f.source)],cancel:PackCancellation())
    let file=try store.file(pack,index:0);XCTAssertEqual((try FileManager.default.attributesOfItem(atPath:file.path)[.posixPermissions] as? NSNumber)?.intValue,0o400)
  }
  func testQueuedGenericRequestClearsBeforeWorkerOnStopAndPrivacy()throws{for change in [nil,PrivacyChange.lock,.privateSession,.identityReset] as [PrivacyChange?]{let f=try Fixture(),c=controller(),q=Queue(),api=Backend(),p=try prompt(),request=GenericReplyRequest(latest:"Synthetic request",history:[QwenTurn(role:.assistant,text:"Synthetic context")]);let job=try XCTUnwrap(LlmControllerJob.submit(controller:c,token:c.token!,store:f.store,selection:f.selection,prompt:p,api:api.api,open:f.open,schedule:q.schedule,workerAllowed:{true},request:request,consume:{_ in XCTFail("cancelled output")}));if let change{_ = c.privacyTransition(change)}else{c.stop()};XCTAssertTrue(request.latest.isEmpty);XCTAssertTrue(request.history.isEmpty);XCTAssertTrue(p.cleared);XCTAssertEqual(f.opens,0);q.start();XCTAssertEqual(job.awaitCompletion(timeout:5),.cancelled);XCTAssertEqual(f.opens,0)}}

}
