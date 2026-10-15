import Foundation

@main struct NativeVadWorkerProbe {
  static func require(_ value: Bool) { if !value { exit(2) } }
  static func main() throws {
    require(CommandLine.arguments.count == 2)
    let model = CommandLine.arguments[1], base = NativeVadAPI.linked
    var valid = true, revokeAfter = false, revokeOnClose = false
    var opens = 0, closes = 0, calls = 0
    let api = NativeVadAPI(create: { path in
      let handle = base.create(path); if handle != nil { opens += 1 }; return handle
    }, process: { h, pcm, final in
      calls += 1; let frame = base.process(h,pcm,final)
      if revokeAfter { valid = false }; return frame
    }, destroy: { h in
      closes += 1; base.destroy(h); if revokeOnClose { valid = false }
    })
    func delivery() -> VadWindowDelivery {
      VadWindowDelivery(allowed: { valid }, open: { try NativeVadStream(model:model,verified:{valid},api:api) })
    }
    func feed(_ d: VadWindowDelivery, count: Int, start: Int) -> VadDeliveryEvent {
      [Float](repeating:0,count:count).withUnsafeBufferPointer { d.accept($0,startSample:start) }
    }
    let quiet = delivery()
    for i in 0..<250 {
      let event = feed(quiet,count:320,start:i*320)
      require(event.result == (i==249 ? .noSpeech : .continued) && event.consumedSamples==320)
    }
    require(quiet.acceptedSamples==80000 && quiet.retainedSamples==0 && opens==1 && closes==1)
    let odd = delivery(); let sizes=[1,511,320,1600,73]
    var position=0,index=0,last=EndpointResult.continued
    while last == .continued {
      let count=sizes[index%sizes.count],event=feed(odd,count:count,start:position)
      require(event.consumedSamples>0 && event.consumedSamples<=count)
      position+=event.consumedSamples;last=event.result;index+=1
    }
    require(position==80000 && last == .noSpeech && odd.retainedSamples==0)
    let eof=delivery();require(feed(eof,count:7,start:0).result == .continued)
    require(eof.finish().result == .incomplete && eof.acceptedSamples==7 && eof.retainedSamples==0)
    let revoked=delivery();revokeAfter=true
    let rejected=feed(revoked,count:512,start:0)
    require(rejected.result == .invalid && rejected.consumedSamples==0 && revoked.retainedSamples==0)
    valid=true;revokeAfter=false;let before=calls
    require(feed(revoked,count:512,start:0).result == .invalid && calls==before)
    let cleanup=delivery();require(feed(cleanup,count:7,start:0).result == .continued)
    revokeOnClose=true;require(cleanup.finish().result == .invalid && cleanup.retainedSamples==0)
    valid=true;require(cleanup.finish().result == .invalid)
    require(opens==5 && closes==5 && calls==317)
    print("{\"scope\":\"IOS_SIMULATOR_NATIVE_WORKER\",\"synthetic\":true,\"quiet_valid_samples\":80000,\"odd_chunk_valid_samples\":80000,\"eof_valid_samples\":7,\"native_calls\":317,\"opens\":5,\"closes\":5,\"revocation_rejected\":true,\"cleanup_revocation_rejected\":true,\"physical\":\"NOT_RUN\"}")
  }
}
