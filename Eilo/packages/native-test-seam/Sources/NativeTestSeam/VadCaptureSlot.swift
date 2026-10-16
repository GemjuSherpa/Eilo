import Foundation

/// Controller-revocable capability. Cancellation signals transport only, never joins inference.
final class VadCapturePermit: @unchecked Sendable {
  private let lock=NSLock()
  private var valid=true
  var cancel: () -> Void = {}
  var active: Bool { lock.lock(); defer { lock.unlock() }; return valid }
  func revoke() { lock.lock(); let notify=valid; valid=false; lock.unlock(); if notify { cancel() } }
}

/// One capture-run slot. Stop closes it permanently; detach invalidates in-flight setup epochs.
final class VadCaptureSlot: @unchecked Sendable {
  let sampleRate: Int
  private let lock=NSLock()
  private var live=true,epoch:UInt64=0
  private var binding:(VadCapturePermit,VadCaptureTransport)?
  init(sampleRate:Int) { self.sampleRate=sampleRate }
  /// Mint before scheduling or hashing. A detach invalidates every outstanding ticket.
  struct SetupTicket {
    fileprivate let slot:VadCaptureSlot,epoch:UInt64
    let capture:any ControllerEffects,controller:NativeController,token:GenerationToken
    func current()->Bool { slot.current(self) && controller.recognitionAllowed(token) }
  }
  func prepare(capture:any ControllerEffects,controller:NativeController,token:GenerationToken)->SetupTicket? {
    guard controller.recognitionAllowed(token) else{return nil}
    lock.lock();defer{lock.unlock()}
    guard live,binding==nil else{return nil}
    return SetupTicket(slot:self,epoch:epoch,capture:capture,controller:controller,token:token)
  }
  private func current(_ ticket:SetupTicket)->Bool {
    lock.lock();defer{lock.unlock()}
    return ticket.slot === self && live && binding==nil && epoch==ticket.epoch && !ticket.token.cancelled
  }
  /// Explicit native-only setup on an inference worker. No normal app caller/readiness override.
  func install(capture:any ControllerEffects,controller:NativeController,token:GenerationToken,
               schedule:@escaping (@escaping ()->Void)->Void,verified:@escaping ()->Bool={false},
               open:@escaping (@escaping ()->Bool)throws->VadStream={_ in throw VadFailure.unavailable},
               accepted:@escaping (VadCaptureOutcome)->Void={_ in},
               openAsr:((@escaping ()->Bool)throws->AsrStream)?=nil,
               recognized:@escaping (AsrText)->Void={_ in},asrVerified:@escaping ()->Bool={false},setup:SetupTicket?=nil,revoked:@escaping ()->Void={}) -> Bool {
    guard (sampleRate==16000 || sampleRate==48000),verified(),(openAsr == nil || asrVerified()),!token.cancelled else { return false }
    lock.lock(); let ticket=setup?.epoch ?? epoch,ready=live && binding==nil && (setup == nil || (setup!.slot === self && setup!.capture === capture && setup!.controller === controller && setup!.token === token && setup!.epoch==epoch)); lock.unlock()
    guard ready else { return false }
    let permit=VadCapturePermit()
    let check={permit.active && !token.cancelled && verified() && (openAsr == nil || asrVerified())}
    let audioFactory:(()->VadAsrHandoff)?=openAsr.map{factory in
      {VadAsrHandoff(token:token,allowed:check,open:{try factory(check)})}
    }
    let transport=VadCaptureTransport(schedule:schedule,verified:check,open:{try open(check)},output:{[weak self] outcome,current in
      _=controller.finishVadCapture(permit,token:token,outcome:outcome,active:current,accepted:accepted)
      self?.retire(permit)
    },failure:{[weak self] current in
      _=controller.failVadCapture(permit,token:token,active:current)
      self?.retire(permit)
    },audioFactory:audioFactory,joinedOutput:audioFactory == nil ? nil : {[weak self] outcome,text,current in
      _=controller.finishVadCapture(permit,token:token,outcome:outcome,active:current,accepted:{value in
        if let text{recognized(text)};if current(){accepted(value)}
      })
      self?.retire(permit)
    },sourceRate:sampleRate)
    permit.cancel={ [weak transport] in revoked();transport?.close() }
    guard controller.prepareVadCapture(permit,capture:capture,token:token) else { transport.close();return false }
    let stillVerified=check()
    lock.lock()
    let attached=stillVerified && live && epoch==ticket && binding==nil && permit.active && !token.cancelled
    if attached { binding=(permit,transport);epoch &+= 1 }
    lock.unlock()
    if !attached { controller.abandonVadCapture(permit);transport.close() }
    return attached
  }
  func submit(_ pcm:UnsafeBufferPointer<Float>,sampleRate:Int) {
    lock.lock();let current=live ? binding?.1:nil;lock.unlock()
    _=current?.submit(pcm,sampleRate:sampleRate)
  }
  func finish() { lock.lock();let current=binding?.1;lock.unlock();current?.finish() }
  private func retire(_ permit:VadCapturePermit) {
    lock.lock();let previous=binding?.0 === permit ? binding:nil
    if previous != nil {binding=nil;epoch &+= 1};lock.unlock();previous?.0.revoke()
  }
  func detach() {
    lock.lock();let previous=binding;binding=nil;epoch &+= 1;lock.unlock()
    previous?.0.revoke();previous?.1.close()
  }
  func close() { lock.lock();live=false;lock.unlock();detach() }
}
