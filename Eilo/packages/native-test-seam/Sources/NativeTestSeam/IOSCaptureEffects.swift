#if os(iOS)
import AVFAudio
import UIKit

/// Native-only capture. Optional verified wake delivery stays off until explicitly attached.
public final class IOSCaptureEffects: ControllerEffects, @unchecked Sendable {
  private let lock=NSRecursiveLock()
  private let worker=DispatchQueue(label:"eilo.native.capture")
  private var run: UInt64=0
  private var standby:StandbyAudioBuffer?
  private var wakeSlot:WakeCaptureSlot?
  private weak var wakeController:NativeController?
  private var expiry:DispatchSourceTimer?
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
        guard format.sampleRate.isFinite,format.sampleRate>=8000,format.sampleRate<=192000,format.sampleRate.rounded()==format.sampleRate,format.channelCount > 0,format.commonFormat == .pcmFormatFloat32 else { throw CaptureFailure.unavailable }
        let retained=StandbyAudioBuffer(sampleRate:Int(format.sampleRate));let ticket=retained.begin()
        let slot=WakeCaptureSlot(sampleRate:Int(format.sampleRate))
        lock.lock();guard run==expected else { lock.unlock();retained.close();try session.setActive(false,options:.notifyOthersOnDeactivation);deliver { completion(false) };return };standby=retained;wakeSlot=slot;lock.unlock()
        input.installTap(onBus:0,bufferSize:512,format:format) { buffer,_ in
          // Retain at most two seconds in the native ring; erase callback samples.
          // Ring tickets reject callbacks after Stop or a new capture.
          if let channels=buffer.floatChannelData {
            let samples=UnsafeBufferPointer(start:channels[0],count:Int(buffer.frameLength))
            retained.append(ticket:ticket,input:samples)
            if buffer.format.sampleRate.isFinite,buffer.format.sampleRate.rounded()==buffer.format.sampleRate,
              (8000...192000).contains(buffer.format.sampleRate) {
              slot.submit(samples,sampleRate:Int(buffer.format.sampleRate))
            } else { slot.submit(samples,sampleRate:0) }
            for channel in 0..<Int(buffer.format.channelCount) {
              channels[channel].update(repeating:0,count:Int(buffer.frameLength))
            }
          }
        }
        lock.lock()
        do {
          guard run == expected,eligible() else { retained.close();slot.close();if run==expected {standby=nil;wakeSlot=nil};lock.unlock();audio.inputNode.removeTap(onBus:0);try session.setActive(false,options:.notifyOthersOnDeactivation);deliver { completion(false) };return }
          try audio.start();engine=audio
          let timer=DispatchSource.makeTimerSource(queue:worker);timer.schedule(deadline:.now(),repeating:.milliseconds(50));timer.setEventHandler { [weak self,weak retained,weak slot] in
            retained?.expire()
            guard let self,let slot else { return }
            // Decode returns before controller entry, so Stop cannot form a controller/decoder lock cycle.
            let result=slot.drain()
            switch result {
            case .events(let events):
              self.lock.lock();let controller=self.wakeController;self.lock.unlock()
              if let controller { for event in events { _=event.apply(controller) } }
            case .failed: if self.current(expected) { self.deliver(failure) }
            case .inactive: break
            }
          };expiry=timer;timer.resume();lock.unlock()
          deliver { completion(true) }
        } catch { lock.unlock();throw error }
      } catch {
        lock.lock();if run==expected { expiry?.cancel();expiry=nil;standby?.close();standby=nil;wakeSlot?.close();wakeSlot=nil;wakeController=nil };lock.unlock()
        candidate?.stop();candidate?.inputNode.removeTap(onBus:0)
        try? AVAudioSession.sharedInstance().setActive(false,options:.notifyOthersOnDeactivation)
        if current(expected) { deliver(failure) }
      }
    }
  }
  private func deliver(_ action: @escaping ()->Void) { DispatchQueue.global(qos:.userInitiated).async(execute:action) }
  private func current(_ expected: UInt64) -> Bool { lock.lock();defer { lock.unlock() };return run == expected }
  /// Native worker setup only; caller supplies an independently verified detector and current token.
  /// The default AppDelegate never calls this while production model readiness is missing.
  func connectWakeDetector(_ detector:WakeDetector,token:GenerationToken,controller:NativeController,completion:@escaping (Bool)->Void) {
    lock.lock();let expected=run,slot=wakeSlot;lock.unlock()
    worker.async { [weak self] in
      guard let self,let slot,self.current(expected),!token.cancelled,
        controller.effects === self,controller.token === token,controller.state == .standby else {
        detector.close();completion(false);return
      }
      do {
        let delivery=try WakeFrameDelivery(sampleRate:slot.sampleRate,detector:detector,token:token)
        self.lock.lock()
        let attached=self.run==expected && self.eligible() && !token.cancelled && slot.attach(delivery)
        if attached { self.wakeController=controller }
        self.lock.unlock()
        if !attached { delivery.close() }
        completion(attached)
      } catch { detector.close();completion(false) }
    }
  }
  public func releaseCapture() throws {
    lock.lock();defer { lock.unlock() };run &+= 1
    expiry?.cancel();expiry=nil;standby?.close();standby=nil;wakeSlot?.close();wakeSlot=nil;wakeController=nil
    if let audio=engine { engine=nil;audio.stop();audio.inputNode.removeTap(onBus:0);try AVAudioSession.sharedInstance().setActive(false,options:.notifyOthersOnDeactivation) }
  }
  public func cancelWork() throws { lock.lock();defer { lock.unlock() };wakeSlot?.detach();wakeController=nil }
  public func clearVolatileContext() throws { lock.lock();defer { lock.unlock() };standby?.clear();wakeSlot?.detach();wakeController=nil }
  public func playClause(_ clause:String) throws { throw CaptureFailure.unavailable }
  private enum CaptureFailure: Error { case unavailable }
}
public final class IOSCaptureEligibility: @unchecked Sendable {
  private let lock=NSLock();private var foreground=false;private var unlocked=false
  public var visible: Bool { get { lock.lock();defer { lock.unlock() };return foreground } set { lock.lock();foreground=newValue;lock.unlock() } }
  public func protectedData(_ available: Bool) { lock.lock();unlocked=available;lock.unlock() }
  public var allowed: Bool { lock.lock();defer { lock.unlock() };return BackgroundCapturePolicy.allows(visible:foreground,unlocked:unlocked,permission:true,consent:false,capabilityVerified:BackgroundCapturePolicy.iosPhysicalPolicyVerified) }
}
#endif
