import Foundation
import CryptoKit
import Darwin

/// Reviewed native configuration, never selected by JS or manifest array order.
struct LlmArtifactPin {
  let id, sha256, licenseEvidence: String
  let bytes: Int64
  init(id: String, sha256: String, bytes: Int64, licenseEvidence: String) throws {
    func matches(_ text: String, _ pattern: String) -> Bool {
      text.range(of: pattern, options: .regularExpression) == text.startIndex..<text.endIndex
    }
    guard matches(id, "[a-z0-9][a-z0-9-]{0,63}"), matches(sha256, "[a-f0-9]{64}"),
      matches(licenseEvidence, "[a-f0-9]{64}"), (1...8_000_000_000).contains(bytes) else { throw LlmFailure.unavailable }
    self.id = id; self.sha256 = sha256; self.bytes = bytes; self.licenseEvidence = licenseEvidence
  }
}
struct LlmPackSelection {
  let packID, runtimeRevision: String
  let model: LlmArtifactPin
  init(packID: String, runtimeRevision: String, model: LlmArtifactPin) throws {
    guard packID.range(of: "[a-z0-9][a-z0-9-]{0,63}", options: .regularExpression) == packID.startIndex..<packID.endIndex,
      runtimeRevision.range(of: "[a-f0-9]{40}", options: .regularExpression) == runtimeRevision.startIndex..<runtimeRevision.endIndex else { throw LlmFailure.unavailable }
    self.packID = packID; self.runtimeRevision = runtimeRevision; self.model = model
  }
}
final class LlmVerifiedDescriptor {
  let value: Int32
  private var closed = false
  private let release: () throws -> Void
  init(_ value: Int32, release: @escaping () throws -> Void) { self.value = value; self.release = release }
  func close() throws {
    guard !closed else { return }; closed = true
    do { try release() } catch { throw LlmFailure.unavailable }
  }
  deinit { try? close() }
}
enum LlmModelDescriptor {
  static func open(_ file: URL, _ pin: LlmArtifactPin) throws -> LlmVerifiedDescriptor {
    let fd = Darwin.open(file.path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC | O_NONBLOCK)
    guard fd >= 0 else { throw LlmFailure.unavailable }
    var transferred = false
    defer { if !transferred { Darwin.close(fd) } }
    var scratch = [UInt8](repeating: 0, count: 65536)
    defer { scratch.withUnsafeMutableBufferPointer { $0.initialize(repeating: 0) } }
    var info = stat(), total: Int64 = 0, hash = SHA256()
    guard fstat(fd, &info) == 0, info.st_mode & S_IFMT == S_IFREG, info.st_size == pin.bytes else { throw LlmFailure.unavailable }
    while true {
      let count = scratch.withUnsafeMutableBytes { Darwin.read(fd, $0.baseAddress, $0.count) }
      guard count >= 0 else { throw LlmFailure.unavailable }; if count == 0 { break }
      total += Int64(count); guard total <= pin.bytes else { throw LlmFailure.unavailable }
      scratch.withUnsafeBytes { hash.update(bufferPointer: UnsafeRawBufferPointer(rebasing: $0[..<count])) }
    }
    guard total == pin.bytes, fstat(fd, &info) == 0, info.st_size == pin.bytes,
      hash.finalize().map({ String(format: "%02x", $0) }).joined() == pin.sha256,
      lseek(fd, 0, SEEK_SET) == 0 else { throw LlmFailure.unavailable }
    transferred = true
    return LlmVerifiedDescriptor(fd) { guard Darwin.close(fd) == 0 else { throw LlmFailure.unavailable } }
  }
}

/// Resolve/open on one native worker; borrow-time verification is disk-free.
/// Slots must remain app-private/immutable. Revoke before known maintenance.
/// The controller separately cancels an active native call and joins its worker.
final class LlmPackLease {
  private let store: PackStore, epoch: UUID, file: URL, pin: LlmArtifactPin
  private let lock = NSLock()
  private var active = true
  private init(store: PackStore, epoch: UUID, file: URL, pin: LlmArtifactPin) {
    self.store = store; self.epoch = epoch; self.file = file; self.pin = pin
  }
  func verified() -> Bool {
    lock.lock(); let current = active; lock.unlock()
    return current && store.epoch == epoch
  }
  func close() { lock.lock(); active = false; lock.unlock() }
  static func resolve(store: PackStore, selection: LlmPackSelection) throws -> LlmPackLease {
    do {
      let epoch = store.epoch
      guard let snapshot = try store.verifiedFiles() else { throw LlmFailure.unavailable }
      let manifest = snapshot.0.manifest, pin = selection.model
      guard manifest.packID == selection.packID, manifest.runtimeRevision == selection.runtimeRevision,
        let index = manifest.artifacts.firstIndex(where: { $0.id == pin.id }) else { throw LlmFailure.unavailable }
      let artifact = manifest.artifacts[index]
      guard artifact.role == "llm", artifact.filename.hasSuffix(".gguf"), artifact.sha256 == pin.sha256,
        artifact.bytes == pin.bytes, artifact.license == "Apache-2.0", artifact.licenseEvidence == pin.licenseEvidence,
        store.epoch == epoch else { throw LlmFailure.unavailable }
      return LlmPackLease(store: store, epoch: epoch, file: snapshot.1[index], pin: pin)
    } catch { throw LlmFailure.unavailable }
  }
  func openStream(allowed: @escaping () -> Bool, threads: Int = 2, api: NativeLlmAPI = .linked,
                  openDescriptor: (URL, LlmArtifactPin) throws -> LlmVerifiedDescriptor = LlmModelDescriptor.open) throws -> NativeLlmStream {
    func current() -> Bool { verified() && allowed() }
    guard current(), (1...8).contains(threads) else { throw LlmFailure.unavailable }
    var stream: NativeLlmStream?, descriptor: LlmVerifiedDescriptor?
    do {
      let owned = try openDescriptor(file, pin); descriptor = owned
      guard current(), owned.value >= 0 else { throw LlmFailure.unavailable }
      let candidate = try NativeLlmStream(allowed: current, api: api); stream = candidate
      try candidate.load(verifiedDescriptor: owned.value, threads: threads)
      try owned.close(); descriptor = nil
      guard current() else { throw LlmFailure.unavailable }
      return candidate
    } catch {
      try? descriptor?.close(); stream?.close()
      throw (error as? LlmFailure) ?? LlmFailure.unavailable
    }
  }
}
