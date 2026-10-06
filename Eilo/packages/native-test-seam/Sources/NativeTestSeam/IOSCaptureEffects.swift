#if os(iOS)
import AVFAudio
import UIKit

/// Native-only capture. No audio leaves this adapter until separately reviewed wake/ASR work.
public final class IOSCaptureEffects: ControllerEffects, @unchecked Sendable {
  private let lock=NSRecursiveLock()
  private let worker=DispatchQueue(label:"eilo.native.capture")
  private var run: UInt64=0
  private var engine: AVAudioEngine?
  private var speechGain:Float=1
  public func setOutputGain(_ gain:Float) throws { lock.lock();defer { lock.unlock() };guard gain.isFinite,(0...1).contains(gain) else { throw CaptureFailure.unavailable };speechGain=gain }
  public var eligible: () -> Bool = { false }
  public init() {}
  public func startCapture() throws -> Bool { false }
  public func beginCapture(completion: @escaping (Bool)->Void, failure: @escaping ()->Void) throws {
    lock.lock();run &+= 1;let expected=run;lock.unlock()
    worker.async { [self] in
      var candidate: AVAudioEngine?
      do {
        guard current(expected), eligible() else { deliver { completion(false) };return }
        let session=AVAudioSession.sharedInstance()
        try session.setCategory(.playAndRecord,mode:.voiceChat,options:[.allowBluetoothHFP])
        try session.setActive(true)
        let audio=AVAudioEngine();candidate=audio
        let input=audio.inputNode
        let format=input.outputFormat(forBus:0)
        guard format.sampleRate > 0,format.channelCount > 0,format.commonFormat == .pcmFormatFloat32 else { throw CaptureFailure.unavailable }
        input.installTap(onBus:0,bufferSize:512,format:format) { buffer,_ in
          // Discard and erase native samples; no persistence or JS event.
          if let channels=buffer.floatChannelData {
            for channel in 0..<Int(buffer.format.channelCount) {
              channels[channel].update(repeating:0,count:Int(buffer.frameLength))
            }
          }
        }
        lock.lock()
        do {
          guard run == expected,eligible() else { lock.unlock();audio.inputNode.removeTap(onBus:0);try session.setActive(false,options:.notifyOthersOnDeactivation);deliver { completion(false) };return }
          try audio.start();engine=audio;lock.unlock()
          deliver { completion(true) }
        } catch { lock.unlock();throw error }
      } catch {
        candidate?.stop();candidate?.inputNode.removeTap(onBus:0)
        try? AVAudioSession.sharedInstance().setActive(false,options:.notifyOthersOnDeactivation)
        if current(expected) { deliver(failure) }
      }
    }
  }
  private func deliver(_ action: @escaping ()->Void) { DispatchQueue.global(qos:.userInitiated).async(execute:action) }
  private func current(_ expected: UInt64) -> Bool { lock.lock();defer { lock.unlock() };return run == expected }
  public func releaseCapture() throws {
    lock.lock();defer { lock.unlock() };run &+= 1
    if let audio=engine { engine=nil;audio.stop();audio.inputNode.removeTap(onBus:0);try AVAudioSession.sharedInstance().setActive(false,options:.notifyOthersOnDeactivation) }
  }
  public func cancelWork() throws {}
  public func clearVolatileContext() throws {}
  public func playClause(_ clause:String) throws { throw CaptureFailure.unavailable }
  private enum CaptureFailure: Error { case unavailable }
}
public final class IOSCaptureEligibility: @unchecked Sendable {
  private let lock=NSLock();private var foreground=false;private var unlocked=false
  public var visible: Bool { get { lock.lock();defer { lock.unlock() };return foreground } set { lock.lock();foreground=newValue;lock.unlock() } }
  public func protectedData(_ available: Bool) { lock.lock();unlocked=available;lock.unlock() }
  public var allowed: Bool { lock.lock();defer { lock.unlock() };return foreground && unlocked }
}
#endif
