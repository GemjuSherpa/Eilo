import Foundation

@main struct NativeVadCaptureProbe {
  static func require(_ value:Bool){if !value{exit(2)}}
  static func main() throws {
    require(CommandLine.arguments.count==2)
    let model=CommandLine.arguments[1],base=NativeVadAPI.linked
    let worker=DispatchQueue(label:"eilo.synthetic.vad.capture"),key=DispatchSpecificKey<Bool>()
    worker.setSpecific(key:key,value:true)
    var valid=true,revokeOnClose=false,stopDuring=false
    var stop:()->Void={}
    var opens=0,closes=0,calls=0,failures=0
    var events=[VadCaptureOutcome]()
    let api=NativeVadAPI(create:{path in
      require(DispatchQueue.getSpecific(key:key)==true)
      let h=base.create(path);if h != nil{opens+=1};return h
    },process:{h,pcm,final in
      require(DispatchQueue.getSpecific(key:key)==true);calls+=1
      let frame=base.process(h,pcm,final);if stopDuring{stop()};return frame
    },destroy:{h in
      require(DispatchQueue.getSpecific(key:key)==true);closes+=1;base.destroy(h)
      if revokeOnClose{valid=false}
    })
    func transport()->VadCaptureTransport {
      VadCaptureTransport(schedule:{worker.async(execute:$0)},verified:{valid},
        open:{try NativeVadStream(model:model,verified:{valid},api:api)},
        output:{value,current in require(current());events.append(value)},failure:{current in require(current());failures+=1})
    }
    func feed(_ d:VadCaptureTransport,count:Int=320) {
      require([Float](repeating:0,count:count).withUnsafeBufferPointer{d.submit($0,sampleRate:16000)})
      worker.sync{}
    }
    let quiet=transport()
    for _ in 0..<250{feed(quiet)}
    require(events.count==1 && events[0].result == .noSpeech && events[0].totalSamples==80000 && events[0].lastChunkConsumed==320)
    require(quiet.retainedSamples==0);quiet.close();worker.sync{}
    let eof=transport();feed(eof,count:7);eof.finish();worker.sync{}
    require(events.count==2 && events[1].result == .incomplete && events[1].totalSamples==7)
    eof.close();worker.sync{}
    let revoked=transport();stop={revoked.close()};stopDuring=true;feed(revoked,count:512)
    require(events.count==2 && failures==0 && !revoked.current());stopDuring=false;stop={}
    let idle=transport();feed(idle,count:512);let before=closes;idle.close();worker.sync{}
    require(closes==before+1 && !idle.current() && idle.retainedSamples==0)
    let cleanup=transport();feed(cleanup,count:7);revokeOnClose=true;cleanup.finish();worker.sync{}
    require(events.count==2 && failures==1 && !cleanup.current());revokeOnClose=false;valid=true
    require(opens==5 && closes==5 && calls==161)
    print("{\"scope\":\"IOS_SIMULATOR_CAPTURE_TRANSPORT\",\"synthetic\":true,\"quiet_valid_samples\":80000,\"eof_valid_samples\":7,\"native_calls\":161,\"opens\":5,\"closes\":5,\"separate_worker_verified\":true,\"stop_during_inference_rejected\":true,\"stop_without_new_frames_closed\":true,\"cleanup_revocation_rejected\":true,\"physical\":\"NOT_RUN\"}")
  }
}
