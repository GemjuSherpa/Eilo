import Foundation

/// Native volatile mono Float PCM. No persistence, ASR, bridge or model consumer.
final class StandbyAudioBuffer:@unchecked Sendable {
    private let lock=NSRecursiveLock();private let now:()->UInt64
    private var samples:[Float];private var receivedAt:[UInt64]
    private var head=0;private var size=0;private var epoch:UInt64=0;private var open=false;private var lastClock:UInt64?
    init(sampleRate:Int,now:@escaping ()->UInt64={DispatchTime.now().uptimeNanoseconds}) {
        precondition((8000...192000).contains(sampleRate));self.now=now
        samples=Array(repeating:0,count:sampleRate*2);receivedAt=Array(repeating:0,count:sampleRate*2)
    }
    func begin()->UInt64 { lock.lock();defer { lock.unlock() };clear();epoch &+= 1;open=true;return epoch }
    func close() { lock.lock();defer { lock.unlock() };open=false;epoch &+= 1;clear() }
    func clear() { lock.lock();defer { lock.unlock() };samples.withUnsafeMutableBufferPointer {$0.initialize(repeating:0)};receivedAt.withUnsafeMutableBufferPointer {$0.initialize(repeating:0)};head=0;size=0;lastClock=nil }
    func expire() {
        lock.lock();defer { lock.unlock() };let time=now()
        if let previous=lastClock,time<previous { clear() };lastClock=time
        while size>0 && time>=receivedAt[head] && time-receivedAt[head]>=2_000_000_000 {
            samples[head]=0;receivedAt[head]=0;head=(head+1)%samples.count;size-=1
        }
    }
    func append(ticket:UInt64,input:UnsafeBufferPointer<Float>) {
        lock.lock();defer { lock.unlock() };guard open,ticket==epoch else { return };expire();let time=now()
        for i in max(0,input.count-samples.count)..<input.count {
            if size==samples.count { samples[head]=0;receivedAt[head]=0;head=(head+1)%samples.count;size-=1 }
            let slot=(head+size)%samples.count;samples[slot]=input[i].isFinite ? input[i] : 0;receivedAt[slot]=time;size+=1
        }
    }
    var count:Int { lock.lock();defer { lock.unlock() };expire();return size }
    func sample(_ index:Int)->Float { lock.lock();defer { lock.unlock() };expire();precondition((0..<size).contains(index));return samples[(head+index)%samples.count] }
}
