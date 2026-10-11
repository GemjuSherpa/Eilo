import Foundation

/// Sequence-addressed native 16 kHz suffix. Worker-owned; borrowed input erased after calls.
final class WakeQuestionHandoff {
 private let lock=NSRecursiveLock()
 private var ring=[Float](repeating:0,count:32000),scratch=[Float](repeating:0,count:32000)
 private var head=0,size=0,next:UInt64=0,initialized=false,active=false,closed=false
 private var token:GenerationToken?;private var valid:()->Bool={false}
 private var sink:((UnsafeBufferPointer<Float>) throws -> Void)?
 func offer(_ input:UnsafeBufferPointer<Float>,startSample:UInt64)->Bool {
  lock.lock();defer{lock.unlock()}
  guard !closed,input.count>0,input.count<=1600,startSample<=UInt64.max-UInt64(input.count),input.allSatisfy({$0.isFinite && (-1...1).contains($0)}) else {close();return false}
  if initialized && startSample>next {close();return false}
  if !initialized {next=startSample;initialized=true}
  let skip=Int(min(UInt64(input.count),next>=startSample ? next-startSample:0))
  if skip==input.count{return true}
  if active {
   guard let expected=token,!expected.cancelled,valid(),let sink else{close();return false}
   for i in skip..<input.count{scratch[i-skip]=input[i]}
   defer{scratch.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
   do {try scratch.withUnsafeBufferPointer{try sink(UnsafeBufferPointer(rebasing:$0[0..<(input.count-skip)]))};guard !expected.cancelled,valid() else{close();return false}}
   catch{close();return false}
  }else {
   for i in skip..<input.count{if size==ring.count{ring[head]=0;head=(head+1)%ring.count;size-=1};ring[(head+size)%ring.count]=input[i];size+=1}
  }
  next=startSample+UInt64(input.count);return true
 }
 func activate(_ expected:GenerationToken,firstQuestionSample:UInt64?,allowed:@escaping ()->Bool,consume:@escaping (UnsafeBufferPointer<Float>) throws->Void)->Bool {
  lock.lock();defer{lock.unlock()}
  guard !closed,!active,!expected.cancelled,allowed(),initialized else{return false}
  let oldest=next-UInt64(size),first=firstQuestionSample ?? (next-UInt64(size))
  guard first>=oldest,first<=next else{close();return false}
  let skip=Int(first-oldest),n=size-skip
  for i in 0..<n{scratch[i]=ring[(head+skip+i)%ring.count]}
  ring.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)};head=0;size=0
  token=expected;valid=allowed;sink=consume;active=true
  defer{scratch.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
  do{if n>0{try scratch.withUnsafeBufferPointer{try consume(UnsafeBufferPointer(rebasing:$0[0..<n]))}};guard !expected.cancelled,allowed() else{close();return false};return true}
  catch{close();return false}
 }
 func close(){lock.lock();defer{lock.unlock()};closed=true;active=false;token=nil;sink=nil;valid={false};ring.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)};scratch.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)};head=0;size=0}
 var retainedSamples:Int{lock.lock();defer{lock.unlock()};return size}
 deinit{close()}
}
