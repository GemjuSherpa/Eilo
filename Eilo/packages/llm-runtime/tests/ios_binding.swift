import Foundation
import CryptoKit
import Darwin

/// Explicit generic evaluator outside the app target; never opens a microphone.
@main struct LlmBindingEvaluation {
  final class Effects: ControllerEffects {
    func startCapture() -> Bool { true } // Synthetic state, no microphone.
    func playClause(_ clause: String) throws { throw LlmFailure.unavailable }
    func cancelWork() {} ; func releaseCapture() {} ; func clearVolatileContext() {}
  }
  struct Permission: MicrophonePermissionAdapter {
    func status() -> MicrophonePermission { .granted }
    func request(_ completion: @escaping (MicrophonePermission) -> Void) { completion(.granted) }
  }
  struct Models: ModelReadinessAdapter { func status() -> ModelStatus { .ready } }
  static func controller() throws -> NativeController {
    let c = NativeController(effects: Effects(), permission: Permission(), models: Models())
    try check(c.dispatch(.start) && c.dispatch(.speechDetected, token:c.token) && c.dispatch(.endpoint, token:c.token)); return c
  }
  static func signedFixture(_ root: URL) throws -> (PackStore,LlmPackSelection) {
    let key = P256.Signing.PrivateKey(), runtime = "8345f333951c661d166b00e6f9362e553768f292", evidence = String(repeating:"c",count:64)
    let hash = CommandLine.arguments[2], size = Int64(CommandLine.arguments[3]) ?? -1, trust = ["evaluation-key":key.publicKey.derRepresentation]
    let store = PackStore(root:root,trust:trust,runtime:runtime,licenseEvidence:[evidence])
    let payload = try JSONSerialization.data(withJSONObject:["schema":1,"packId":"evaluation-pack","revision":1,"runtimeRevision":runtime,
      "minAndroid":35,"minIos":18,"artifacts":[["id":"model","filename":"model.gguf","role":"llm","url":"https://models.example.test/model.gguf",
      "sha256":hash,"bytes":size,"license":"Apache-2.0","licenseEvidence":evidence]]],options:[.sortedKeys,.withoutEscapingSlashes])
    let pack = try VerifiedPack.verify(payload:payload,signature:key.signature(for:payload).derRepresentation,keyID:"evaluation-key",algorithm:"ES256",trust:trust,runtime:runtime)
    try store.activate(pack,proofs:[VerifiedArtifact.verify(pack,index:0,file:URL(fileURLWithPath:CommandLine.arguments[1]))],cancel:PackCancellation())
    return (store,try LlmPackSelection(packID:"evaluation-pack",runtimeRevision:runtime,model:LlmArtifactPin(id:"model",sha256:hash,bytes:size,licenseEvidence:evidence)))
  }
  static func check(_ value: Bool) throws {
    guard value else { throw LlmFailure.unavailable }
  }
  static func cancelled(_ operation: () throws -> Void) throws {
    do { try operation() } catch LlmFailure.cancelled { return }
    throw LlmFailure.unavailable
  }
  static func begin(_ stream: NativeLlmStream, _ prompt: String, limit: Int = 8) throws {
    var bytes = Array(prompt.utf8)
    defer { bytes.withUnsafeMutableBufferPointer { $0.initialize(repeating: 0) } }
    try bytes.withUnsafeBufferPointer { try stream.begin($0, outputLimit: limit) }
  }
  static func verifiedDescriptor(_ path: String, expected: String, size: Int64) throws -> Int32 {
    let fd = Darwin.open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
    guard fd >= 0 else { throw LlmFailure.unavailable }
    do {
      var info = stat()
      try check(fstat(fd, &info) == 0 && (info.st_mode & S_IFMT) == S_IFREG && info.st_size == size)
      var scratch = [UInt8](repeating: 0, count: 65536), hash = SHA256()
      while true {
        let count = scratch.withUnsafeMutableBytes { Darwin.read(fd, $0.baseAddress, $0.count) }
        try check(count >= 0)
        if count == 0 { break }
        scratch.withUnsafeBytes { hash.update(bufferPointer: UnsafeRawBufferPointer(rebasing: $0[..<count])) }
      }
      scratch.withUnsafeMutableBufferPointer { $0.initialize(repeating: 0) }
      try check(hash.finalize().map { String(format: "%02x", $0) }.joined() == expected)
      try check(lseek(fd, 0, SEEK_SET) == 0)
      return fd // The same hashed descriptor is borrowed by the real C adapter.
    } catch { Darwin.close(fd); throw LlmFailure.unavailable }
  }
  static func make(_ fd: Int32, allowed: @escaping () -> Bool = { true },
                   api: NativeLlmAPI = .linked) throws -> NativeLlmStream {
    let stream = try NativeLlmStream(allowed: allowed, api: api)
    do { try stream.load(verifiedDescriptor: fd); return stream }
    catch { stream.close(); throw error }
  }
  static func concurrentCancellation(_ fd: Int32, loading: Bool) throws {
    let real = NativeLlmAPI.linked, entered = DispatchSemaphore(value: 0)
    let joined = DispatchGroup()
    let api = NativeLlmAPI(create: real.create,
      load: { h, fd, threads in if loading { entered.signal() }; return real.load(h, fd, threads) },
      begin: { h, prompt, limit in if !loading { entered.signal() }; return real.begin(h, prompt, limit) },
      next: real.next, cancel: real.cancel, destroy: real.destroy)
    let stream = try NativeLlmStream(allowed: { true }, api: api)
    defer { stream.close() }
    if !loading { try stream.load(verifiedDescriptor: fd) }
    joined.enter()
    DispatchQueue.global().async {
      if entered.wait(timeout: .now() + 10) == .success {
        usleep(2000); stream.requestCancellation()
      }
      joined.leave()
    }
    // A fast native call may finish before cancellation; either way, no later
    // piece may escape once cancellation is joined. This is not a latency trial.
    do {
      if loading { try stream.load(verifiedDescriptor: fd) }
      else { try begin(stream, String(repeating: " A", count: 1500)) }
    } catch LlmFailure.cancelled { }
    try check(joined.wait(timeout: .now() + 10) == .success)
    try cancelled { _ = try stream.withNextPiece { _ in fatalError("cancelled fixture released") } }
  }
  static func run() throws {
    try check(CommandLine.arguments.count == 5)
    let fd = try verifiedDescriptor(CommandLine.arguments[1], expected: CommandLine.arguments[2],
                                    size: Int64(CommandLine.arguments[3]) ?? -1)
    defer { Darwin.close(fd) }
    let corrupt = Darwin.open(CommandLine.arguments[4], O_RDONLY | O_NOFOLLOW | O_CLOEXEC)
    try check(corrupt >= 0); defer { Darwin.close(corrupt) }
    let prompts = ["The opposite of cold is", "One, two, three,", "The sky on a clear day is"]
    let root = FileManager.default.temporaryDirectory.appendingPathComponent("eilo-llm-evaluation-"+UUID().uuidString)
    defer { try? FileManager.default.removeItem(at:root) }
    let (store,selection) = try signedFixture(root)
    for (index, prompt) in prompts.enumerated() {
      let c = try controller()
      var input = Array(try QwenTemplate.render(latest:prompt).utf8)
      let owned = try input.withUnsafeBufferPointer { try LlmOwnedPrompt($0) }
      input.withUnsafeMutableBufferPointer { $0.initialize(repeating:0) }
      var output = [UInt8](), count = 0
      let guardOutput = NonThinkingOutput(current:{c.token.map{!$0.cancelled} ?? false}){output.append(contentsOf:$0.utf8)}
      guard let job = LlmControllerJob.submit(controller:c,token:c.token!,store:store,selection:selection,prompt:owned,outputLimit:8,consume:{ bytes in
        try check(!Thread.isMainThread);try guardOutput.append(bytes);count += 1;try check(count <= 8)
      }) else { throw LlmFailure.unavailable }
      try check(job.awaitCompletion(timeout:120) == .completed && owned.cleared && c.state == .thinking)
      try guardOutput.finish()
      try check(eilo_llm_eval_cpu_only() == 1 && count > 0 && !output.isEmpty)
      print("GEN\t\(index + 1)\t\(count)\t\(output.map { String(format: "%02x", $0) }.joined())")
      output.withUnsafeMutableBufferPointer { $0.initialize(repeating: 0) }
    }
    let budgetStream = try make(fd)
    let plan = try PromptBudget.build(latest:"Name one colour.",history:(0..<16).map{_ in QwenTurn(role:.user,text:String(repeating:"Generic earlier context. ",count:100))},recall:(0..<6).map{_ in String(repeating:"Generic recalled fact. ",count:60)},memoryAllowed:true,count:budgetStream.countTokens)
    try check(plan.promptTokens+plan.outputLimit<=4096 && plan.recalledTokens<=512 && plan.droppedHistory>0 && plan.droppedRecall>0 && plan.text.contains(QwenTemplate.rules) && plan.text.contains("Name one colour."))
    try check(try budgetStream.countTokens(plan.text)==plan.promptTokens)
    try begin(budgetStream,plan.text);try check(try budgetStream.withNextPiece{_ in});budgetStream.close()
    let pre = try NativeLlmStream(allowed: { true }); pre.requestCancellation()
    try cancelled { try pre.load(verifiedDescriptor: fd) }; pre.close()
    do { let invalid = try make(corrupt); invalid.close(); throw LlmFailure.cancelled }
    catch LlmFailure.unavailable { }
    let post = try make(fd); try begin(post, prompts[0])
    try check(try post.withNextPiece { _ in }); post.requestCancellation()
    try cancelled { _ = try post.withNextPiece { _ in fatalError("post-cancel fixture released") } }; post.close()
    var valid = true
    let real = NativeLlmAPI.linked
    let revoke = NativeLlmAPI(create: real.create, load: real.load, begin: real.begin,
      next: { h, buffer, bytes in let result = real.next(h, buffer, &bytes); valid = false; return result },
      cancel: real.cancel, destroy: real.destroy)
    let stale = try make(fd, allowed: { valid }, api: revoke); try begin(stale, prompts[0])
    do { _ = try stale.withNextPiece { _ in fatalError("revoked fixture released") }; throw LlmFailure.cancelled }
    catch LlmFailure.unavailable { }; stale.close()
    try concurrentCancellation(fd, loading: true)
    try concurrentCancellation(fd, loading: false)
    print("LIFECYCLE\tpre_cancel,corrupt_gguf,post_token_cancel,lease_revocation,concurrent_load_cancel,concurrent_begin_cancel\tPASS")
    try FileManager.default.removeItem(at:root);try check(!FileManager.default.fileExists(atPath:root.path))
    print("BUDGET\tactual_vocab,context4096,recall512,output256,preserve_rules_latest\tPASS")
    print("WORKER\tsigned_pack_three_completions,prompt_erased,no_speech,temp_removed\tPASS")
  }
  static func main() {
    do { try run() }
    catch { fputs("LLM binding evaluation unavailable\n", stderr); exit(1) }
  }
}
