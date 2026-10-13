import Foundation
import CryptoKit
import Darwin
import XCTest
@testable import NativeTestSeam

final class LlmPackLeaseTests: XCTestCase {
  private final class Fixture {
    let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
    let key = P256.Signing.PrivateKey(), runtime = String(repeating: "a", count: 40), evidence = String(repeating: "c", count: 64)
    let source, decoy: URL
    let store: PackStore, pin: LlmArtifactPin, selection: LlmPackSelection
    init() throws {
      source = root.appendingPathComponent("source"); decoy = root.appendingPathComponent("decoy")
      try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
      try Data([1, 2, 3, 4]).write(to: source); try Data([5, 6]).write(to: decoy)
      store = PackStore(root: root.appendingPathComponent("store"), trust: ["test-key": key.publicKey.derRepresentation], runtime: runtime, licenseEvidence: [evidence])
      pin = try LlmArtifactPin(id: "model", sha256: Self.digest(source), bytes: 4, licenseEvidence: evidence)
      selection = try LlmPackSelection(packID: "test-pack", runtimeRevision: runtime, model: pin)
    }
    static func digest(_ file: URL) throws -> String {
      SHA256.hash(data: try Data(contentsOf: file)).map { String(format: "%02x", $0) }.joined()
    }
    func pack(_ revision: Int = 1, role: String = "llm", filename: String = "model.gguf", license: String = "Apache-2.0") throws -> VerifiedPack {
      func artifact(_ id: String, _ name: String, _ kind: String, _ file: URL, _ rights: String = "Apache-2.0") throws -> [String: Any] {
        ["id": id, "filename": name, "role": kind, "url": "https://models.example.test/" + name,
         "sha256": try Self.digest(file), "bytes": try Data(contentsOf: file).count, "license": rights, "licenseEvidence": evidence]
      }
      let payload = try JSONSerialization.data(withJSONObject: ["schema": 1, "packId": "test-pack", "revision": revision,
        "runtimeRevision": runtime, "minAndroid": 35, "minIos": 18,
        "artifacts": [artifact("decoy", "decoy.txt", "tokenizer", decoy), artifact("model", filename, role, source, license)]], options: [.sortedKeys, .withoutEscapingSlashes])
      return try VerifiedPack.verify(payload: payload, signature: key.signature(for: payload).derRepresentation,
        keyID: "test-key", algorithm: "ES256", trust: ["test-key": key.publicKey.derRepresentation], runtime: runtime)
    }
    func activate(_ value: VerifiedPack? = nil) throws {
      let pack = try value ?? self.pack()
      try store.activate(pack, proofs: pack.manifest.artifacts.indices.map {
        try VerifiedArtifact.verify(pack, index: $0, file: pack.manifest.artifacts[$0].id == "model" ? source : decoy)
      }, cancel: PackCancellation())
    }
    func lease() throws -> LlmPackLease { try LlmPackLease.resolve(store: store, selection: selection) }
    deinit { try? FileManager.default.removeItem(at: root) }
  }
  private final class Backend {
    var creates = 0, loads = 0, destroys = 0, nexts = 0
    var onCreate: () throws -> Void = {}, onLoad: (Int32) throws -> Int32 = { _ in 0 }, onNext: () throws -> Void = {}
    var api: NativeLlmAPI {
      NativeLlmAPI(create: {
        self.creates += 1; do { try self.onCreate(); return OpaquePointer(bitPattern: 7) } catch { return nil }
      }, load: { _, fd, _ in self.loads += 1; do { return try self.onLoad(fd) } catch { return -3 } },
      begin: { _, _, _ in 0 }, next: { _, out, count in
        self.nexts += 1; out[0] = 65; count = 1
        do { try self.onNext(); return 1 } catch { return -3 }
      }, cancel: { _ in }, destroy: { _ in self.destroys += 1 })
    }
  }
  private final class Opening {
    var opens = 0, closes = 0
    var onOpen: () throws -> Void = {}, onClose: () throws -> Void = {}
    func open(_ file: URL, _ pin: LlmArtifactPin) throws -> LlmVerifiedDescriptor {
      opens += 1; XCTAssertEqual(file.lastPathComponent, "model.gguf"); XCTAssertEqual(try Fixture.digest(file), pin.sha256)
      try onOpen(); return LlmVerifiedDescriptor(31) { self.closes += 1; try self.onClose() }
    }
  }
  private func rejects(_ operation: () throws -> Void, file: StaticString = #filePath, line: UInt = #line) {
    XCTAssertThrowsError(try operation(), file: file, line: line) { error in
      guard case LlmFailure.unavailable = error else { return XCTFail("unexpected typed failure", file: file, line: line) }
    }
  }
  private func begin(_ stream: NativeLlmStream) throws {
    try [UInt8](arrayLiteral: 65).withUnsafeBufferPointer { try stream.begin($0, outputLimit: 8) }
  }
  func testSignedIdChoosesModelAfterDecoyAndClosesDescriptor() throws {
    let f = try Fixture(); try f.activate(); let lease = try f.lease(), backend = Backend(), opening = Opening()
    let stream = try lease.openStream(allowed: { true }, api: backend.api, openDescriptor: opening.open)
    XCTAssertEqual(backend.loads, 1); XCTAssertEqual(opening.closes, 1)
    try begin(stream); XCTAssertTrue(try stream.withNextPiece { XCTAssertEqual(Array($0), [65]) })
    stream.close(); lease.close(); XCTAssertFalse(lease.verified()); XCTAssertEqual(backend.destroys, 1)
  }
  func testMissingUntrustedAndUnlicensedStoreCannotResolve() throws {
    let f = try Fixture(); rejects { _ = try f.lease() }; try f.activate()
    let root = f.root.appendingPathComponent("store")
    for store in [PackStore(root: root, trust: [:], runtime: f.runtime, licenseEvidence: [f.evidence]),
                  PackStore(root: root, trust: ["test-key": f.key.publicKey.derRepresentation], runtime: f.runtime)] {
      rejects { _ = try LlmPackLease.resolve(store: store, selection: f.selection) }
    }
  }
  func testWrongPackRuntimeIdHashSizeAndEvidenceRejected() throws {
    let f = try Fixture(); try f.activate()
    let badPins = [try LlmArtifactPin(id: "absent", sha256: f.pin.sha256, bytes: 4, licenseEvidence: f.evidence),
      try LlmArtifactPin(id: "model", sha256: String(repeating: "d", count: 64), bytes: 4, licenseEvidence: f.evidence),
      try LlmArtifactPin(id: "model", sha256: f.pin.sha256, bytes: 5, licenseEvidence: f.evidence),
      try LlmArtifactPin(id: "model", sha256: f.pin.sha256, bytes: 4, licenseEvidence: String(repeating: "d", count: 64))]
    let selections = try [LlmPackSelection(packID: "other", runtimeRevision: f.runtime, model: f.pin),
      LlmPackSelection(packID: "test-pack", runtimeRevision: String(repeating: "b", count: 40), model: f.pin)] +
      badPins.map { try LlmPackSelection(packID: "test-pack", runtimeRevision: f.runtime, model: $0) }
    for selection in selections { rejects { _ = try LlmPackLease.resolve(store: f.store, selection: selection) } }
  }
  func testSignedWrongRoleExtensionOrLicenseRejected() throws {
    let f = try Fixture()
    try f.activate(f.pack(role: "asr")); rejects { _ = try f.lease() }
    try f.activate(f.pack(2, filename: "model.onnx")); rejects { _ = try f.lease() }
    try f.activate(f.pack(3, license: "MIT")); rejects { _ = try f.lease() }
  }
  func testCorruptArtifactAndSymlinkRejected() throws {
    let f = try Fixture(), pack = try f.pack(); try f.activate(pack)
    let model = try f.store.file(pack, index: 1)
    try Data([9, 9, 9, 9]).write(to: model); rejects { _ = try f.lease() }
    try FileManager.default.removeItem(at: model); try FileManager.default.createSymbolicLink(at: model, withDestinationURL: f.source)
    rejects { _ = try f.lease() }
  }
  func testClosedLeaseAndInvalidThreadsRejectBeforeOpeningOrCreate() throws {
    let f = try Fixture(); try f.activate(); let lease = try f.lease(), backend = Backend(), opening = Opening()
    for threads in [0, 9] { rejects { _ = try lease.openStream(allowed: { true }, threads: threads, api: backend.api, openDescriptor: opening.open) } }
    lease.close(); lease.close(); rejects { _ = try lease.openStream(allowed: { true }, api: backend.api, openDescriptor: opening.open) }
    XCTAssertEqual(opening.opens, 0); XCTAssertEqual(backend.creates, 0)
  }
  func testRejectedControllerDoesNotTouchDescriptor() throws {
    let f = try Fixture(); try f.activate(); let opening = Opening(), backend = Backend()
    rejects { _ = try f.lease().openStream(allowed: { false }, api: backend.api, openDescriptor: opening.open) }
    XCTAssertEqual(opening.opens, 0); XCTAssertEqual(backend.creates, 0)
  }
  func testDescriptorFailureAndUnavailableDefaultAreFailClosed() throws {
    let f = try Fixture(); try f.activate(); let lease = try f.lease(), opening = Opening(), backend = Backend()
    rejects { _ = try lease.openStream(allowed: { true }, api: backend.api, openDescriptor: { _, _ in throw PackFailure.integrity }) }
    XCTAssertEqual(backend.creates, 0)
    rejects { _ = try lease.openStream(allowed: { true }, openDescriptor: opening.open) }; XCTAssertEqual(opening.closes, 1)
  }
  func testRevocationDuringDescriptorOpeningClosesBeforeCreate() throws {
    let f = try Fixture(); try f.activate(); let lease = try f.lease(), backend = Backend(), opening = Opening()
    opening.onOpen = lease.close
    rejects { _ = try lease.openStream(allowed: { true }, api: backend.api, openDescriptor: opening.open) }
    XCTAssertEqual(opening.closes, 1); XCTAssertEqual(backend.creates, 0)
  }
  func testReplacementAndFailedActivationRevokeEvenSameModel() throws {
    let f = try Fixture(); try f.activate(); let old = try f.lease(); try f.activate(f.pack(2)); XCTAssertFalse(old.verified())
    let next = try f.lease(); XCTAssertThrowsError(try f.activate(f.pack(1))); XCTAssertFalse(next.verified())
  }
  func testReplacementDuringCreateOrLoadNeverPublishesHandle() throws {
    for loading in [false, true] {
      let f = try Fixture(); try f.activate(); let lease = try f.lease(), backend = Backend(), opening = Opening()
      if loading { backend.onLoad = { _ in try f.activate(f.pack(2)); return 0 } }
      else { backend.onCreate = { try f.activate(f.pack(2)) } }
      rejects { _ = try lease.openStream(allowed: { true }, api: backend.api, openDescriptor: opening.open) }
      XCTAssertEqual(backend.destroys, 1); XCTAssertEqual(opening.closes, 1)
    }
  }
  func testCloseFailureAndCloseTimeRevocationDoNotPublishLoadedStream() throws {
    for fails in [false, true] {
      let f = try Fixture(); try f.activate(); let lease = try f.lease(), backend = Backend(), opening = Opening()
      opening.onClose = { if fails { throw PackFailure.integrity }; lease.close() }
      rejects { _ = try lease.openStream(allowed: { true }, api: backend.api, openDescriptor: opening.open) }
      XCTAssertEqual(opening.closes, 1); XCTAssertEqual(backend.destroys, 1)
    }
  }
  func testBackendFailureReleasesDescriptorAndHandleExactlyOnce() throws {
    let f = try Fixture(); try f.activate(); let backend = Backend(), opening = Opening(); backend.onLoad = { _ in -3 }
    rejects { _ = try f.lease().openStream(allowed: { true }, api: backend.api, openDescriptor: opening.open) }
    XCTAssertEqual(opening.closes, 1); XCTAssertEqual(backend.destroys, 1)
  }
  func testStopAndPrivacyTransitionsAfterDecodeRejectControllerToken() throws {
    for privacy in [false, true] {
      let f = try Fixture(); try f.activate(); let controller = testController(); XCTAssertTrue(controller.dispatch(.start))
      let token = try XCTUnwrap(controller.token), backend = Backend(), opening = Opening()
      let stream = try f.lease().openStream(allowed: { !token.cancelled }, api: backend.api, openDescriptor: opening.open)
      try begin(stream); backend.onNext = { if privacy { controller.privacyTransition(.privateSession) } else { controller.stop() } }
      rejects { _ = try stream.withNextPiece { _ in XCTFail("stale piece released") } }
      XCTAssertEqual(backend.nexts, 1); XCTAssertEqual(backend.destroys, 1); stream.close()
    }
  }
  func testPackRevokedDuringDecodeRejectsPiece() throws {
    let f = try Fixture(); try f.activate(); let backend = Backend(), opening = Opening(), lease = try f.lease()
    let stream = try lease.openStream(allowed: { true }, api: backend.api, openDescriptor: opening.open)
    try begin(stream); backend.onNext = { try f.activate(f.pack(2)) }
    rejects { _ = try stream.withNextPiece { _ in XCTFail("revoked piece released") } }; XCTAssertEqual(backend.destroys, 1)
  }
  func testRealDescriptorIsHashedRewoundBorrowedAndClosedAfterLoad() throws {
    let f = try Fixture(); try f.activate(); let backend = Backend(); var borrowed: Int32 = -1
    backend.onLoad = { fd in
      borrowed = fd; var bytes = [UInt8](repeating: 0, count: 4)
      XCTAssertNotEqual(fcntl(fd, F_GETFD) & FD_CLOEXEC, 0)
      XCTAssertEqual(bytes.withUnsafeMutableBytes { Darwin.read(fd, $0.baseAddress, $0.count) }, 4)
      XCTAssertEqual(bytes, [1, 2, 3, 4]); return 0
    }
    let stream = try f.lease().openStream(allowed: { true }, api: backend.api)
    XCTAssertGreaterThanOrEqual(borrowed, 0); XCTAssertEqual(fcntl(borrowed, F_GETFD), -1); XCTAssertEqual(errno, EBADF)
    stream.close(); XCTAssertEqual(backend.destroys, 1)
  }
  func testPathReplacementAfterHashCannotSubstituteLoadedDescriptor() throws {
    let f = try Fixture(), pack = try f.pack(); try f.activate(pack)
    let model = try f.store.file(pack, index: 1), backend = Backend()
    backend.onCreate = {
      try FileManager.default.moveItem(at: model, to: f.root.appendingPathComponent("original"))
      try Data([9, 9, 9, 9]).write(to: model)
    }
    backend.onLoad = { fd in
      var bytes = [UInt8](repeating: 0, count: 4)
      XCTAssertEqual(bytes.withUnsafeMutableBytes { Darwin.read(fd, $0.baseAddress, $0.count) }, 4)
      XCTAssertEqual(bytes, [1, 2, 3, 4]); return 0
    }
    let stream = try f.lease().openStream(allowed: { true }, api: backend.api); stream.close()
    XCTAssertEqual(try Data(contentsOf: model), Data([9, 9, 9, 9]))
  }
  func testRealDescriptorRejectsWrongHashSizeSymlinkDirectoryAndFifo() throws {
    let f = try Fixture()
    let badHash = try LlmArtifactPin(id: "model", sha256: String(repeating: "d", count: 64), bytes: 4, licenseEvidence: f.evidence)
    let badSize = try LlmArtifactPin(id: "model", sha256: f.pin.sha256, bytes: 5, licenseEvidence: f.evidence)
    for pin in [badHash, badSize] { rejects { _ = try LlmModelDescriptor.open(f.source, pin) } }
    let link = f.root.appendingPathComponent("link"), fifo = f.root.appendingPathComponent("fifo")
    try FileManager.default.createSymbolicLink(at: link, withDestinationURL: f.source)
    XCTAssertEqual(mkfifo(fifo.path, 0o600), 0)
    for file in [link, f.root, fifo] { rejects { _ = try LlmModelDescriptor.open(file, f.pin) } }
  }
}
