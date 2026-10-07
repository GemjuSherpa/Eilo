import Foundation

struct WakeCaptureActivation {
  fileprivate let activation:WakeActivation
  fileprivate let lease:WakeLease
  func apply(_ controller:NativeController)->Bool { activation.apply(controller,deliveryActive:{lease.active}) }
}
enum WakeDrain { case events([WakeCaptureActivation]), failed, inactive }

/// One native worker consumer; callback only copies. No controller calls while borrowing PCM.
/// Four <=100 ms frames, <=250 ms receive age. Any discontinuity revokes queued activation.
/// The detector is exclusively owned here. Verification must not acquire controller/capture locks.
final class WakeFrameDelivery:@unchecked Sendable {
  let sampleRate:Int
  private let frameCapacity:Int
  private let queue=NSLock(),consumer=NSRecursiveLock()
  private let storage:UnsafeMutableBufferPointer<Float>,scratch:UnsafeMutableBufferPointer<Float>
  private var counts=[Int](repeating:0,count:4),times=[UInt64](repeating:0,count:4)
  private var head=0,size=0,open=true,failed=false,failureReported=false
  private var lastClock:UInt64?
  private let lease=WakeLease(),detector:WakeDetector,token:GenerationToken,now:()->UInt64
  init(sampleRate:Int,detector:WakeDetector,token:GenerationToken,
       now:@escaping ()->UInt64={DispatchTime.now().uptimeNanoseconds}) throws {
    guard (8000...192000).contains(sampleRate) else { throw WakeFailure.unavailable }
    self.sampleRate=sampleRate;frameCapacity=sampleRate/10;self.detector=detector;self.token=token;self.now=now
    storage = .allocate(capacity:frameCapacity*4);scratch = .allocate(capacity:frameCapacity)
    storage.initialize(repeating:0);scratch.initialize(repeating:0)
    guard detector.begin(token) else { close();throw WakeFailure.unavailable }
  }
  /// Never invokes a model/dispatch/controller or retains the caller's buffer.
  @discardableResult func submit(_ input:UnsafeBufferPointer<Float>,sampleRate:Int)->Bool {
    queue.lock();defer { queue.unlock() }
    guard open,!token.cancelled else { return false }
    let time=now()
    guard sampleRate==self.sampleRate,!input.isEmpty,input.count<=frameCapacity,
      size<4,input.allSatisfy({$0.isFinite && (-1...1).contains($0)}),
      lastClock == nil || time>=lastClock!,
      size==0 || (time>=times[head] && time-times[head]<250_000_000) else {
      failLocked();return false
    }
    lastClock=time
    let slot=(head+size)%4
    for i in input.indices { storage[slot*frameCapacity+i]=input[i] }
    counts[slot]=input.count;times[slot]=time;size+=1;return true
  }
  /// Drain on the native worker, then apply returned metadata after this method releases its locks.
  func drain()->WakeDrain {
    consumer.lock();defer { scratch.update(repeating:0);consumer.unlock() }
    var events=[WakeCaptureActivation]()
    for _ in 0..<4 {
      queue.lock()
      if token.cancelled { open=false;lease.revoke();clearLocked() }
      if failed {
        let report = !failureReported;failureReported=true;queue.unlock();detector.close()
        return report ? .failed:.inactive
      }
      guard open else { queue.unlock();detector.close();return .inactive }
      guard size>0 else { queue.unlock();return .events(events) }
      let time=now()
      guard time>=times[head],time-times[head]<250_000_000,lastClock == nil || time>=lastClock! else {
        failLocked();queue.unlock();detector.close();failureReported=true;return .failed
      }
      lastClock=time
      let count=counts[head],offset=head*frameCapacity
      for i in 0..<count { scratch[i]=storage[offset+i];storage[offset+i]=0 }
      counts[head]=0;times[head]=0;head=(head+1)%4;size-=1;queue.unlock()
      let event=detector.process(token,input:UnsafeBufferPointer(start:scratch.baseAddress,count:count),sampleRate:sampleRate)
      scratch.update(repeating:0)
      guard detector.isActive(token) else {
        if token.cancelled { close();return .inactive }
        queue.lock();failLocked();failureReported=true;queue.unlock();detector.close();return .failed
      }
      if let event,lease.active { events.append(WakeCaptureActivation(activation:event,lease:lease)) }
    }
    return .events(events)
  }
  private func clearLocked() { storage.update(repeating:0);for i in 0..<4 { counts[i]=0;times[i]=0 };head=0;size=0;lastClock=nil }
  private func failLocked() { open=false;failed=true;lease.revoke();clearLocked() }
  func close() {
    // Revoke before waiting for a synchronous borrowed decode; queued events cannot win that wait.
    queue.lock();open=false;failed=false;lease.revoke();clearLocked();queue.unlock()
    consumer.lock();scratch.update(repeating:0);detector.close();consumer.unlock()
  }
  deinit { close();storage.deinitialize();storage.deallocate();scratch.deinitialize();scratch.deallocate() }
}

/// Per-capture slot rejects late worker attachment after Stop, without holding its lock during decode.
final class WakeCaptureSlot:@unchecked Sendable {
  let sampleRate:Int
  private let lock=NSLock()
  private var open=true,delivery:WakeFrameDelivery?
  init(sampleRate:Int) { self.sampleRate=sampleRate }
  func attach(_ candidate:WakeFrameDelivery)->Bool {
    lock.lock();defer { lock.unlock() }
    guard open,delivery==nil,candidate.sampleRate==sampleRate else { return false }
    delivery=candidate;return true
  }
  func submit(_ input:UnsafeBufferPointer<Float>,sampleRate:Int) {
    lock.lock();let current=open ? delivery:nil;lock.unlock();current?.submit(input,sampleRate:sampleRate)
  }
  func drain()->WakeDrain {
    lock.lock();let current=open ? delivery:nil;lock.unlock()
    let result=current?.drain() ?? .inactive
    if case .inactive=result { lock.lock();if delivery === current { delivery=nil };lock.unlock() }
    return result
  }
  func detach() { lock.lock();let previous=delivery;delivery=nil;lock.unlock();previous?.close() }
  func close() { lock.lock();open=false;let previous=delivery;delivery=nil;lock.unlock();previous?.close() }
}
