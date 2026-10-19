import Foundation
import CryptoKit
import Darwin

/// Cancellation can be published before a long native load. Destruction stays on the worker.
final class TrialModelCancellation {
  private let lock=NSLock()
  private var stream:NativeLlmStream?,stopped=false
  func publish(_ value:NativeLlmStream){lock.lock();defer{lock.unlock()};stream=value;if stopped{value.requestCancellation()}}
  func cancel(){lock.lock();defer{lock.unlock()};stopped=true;stream?.requestCancellation()}
  func clear(){lock.lock();defer{lock.unlock()};stream=nil}
}

enum TrialModelDiagnostic {
  static let fixtureDigest="0e6bfb28b2bb8f93dfd6a06838fddc0f43a15c8bb1d824ee0988bb3f70ef5746"
  private struct Corpus:Decodable{struct Prompt:Decodable{let id,text:String};let prompts:[Prompt]}
  /// Public OS ledger peak: process lifetime, including model preparation. Never a per-prompt peak.
  static func footprint()throws->[String:Any]{
    var info=task_vm_info_data_t()
    var count=mach_msg_type_number_t(MemoryLayout<task_vm_info_data_t>.size/MemoryLayout<integer_t>.size)
    let result=withUnsafeMutablePointer(to:&info){pointer in
      pointer.withMemoryRebound(to:integer_t.self,capacity:Int(count)){
        task_info(mach_task_self_,task_flavor_t(TASK_VM_INFO),$0,&count)
      }
    }
    let needed=(MemoryLayout<task_vm_info_data_t>.offset(of:\task_vm_info_data_t.ledger_phys_footprint_peak)!+MemoryLayout<UInt64>.size)/MemoryLayout<integer_t>.size
    guard result==KERN_SUCCESS,Int(count)>=needed,info.phys_footprint>0,info.ledger_phys_footprint_peak>=info.phys_footprint else{throw LlmFailure.unavailable}
    return ["current_phys_footprint_bytes":info.phys_footprint,"process_lifetime_peak_bytes":info.ledger_phys_footprint_peak]
  }
  static func run(assets:URL,store:PackStore,selection:LlmPackSelection,cancellation:TrialModelCancellation,allowed:@escaping()->Bool)throws->[[String:Any]]{
    let data=try Data(contentsOf:assets.appendingPathComponent("model-comparison-fixtures.json"))
    guard allowed(),SHA256.hash(data:data).map({String(format:"%02x",$0)}).joined()==fixtureDigest else{throw LlmFailure.unavailable}
    let corpus=try JSONDecoder().decode(Corpus.self,from:data)
    guard corpus.prompts.map({$0.id})==(1...6).map({String(format:"compare-%02d",$0)}) else{throw LlmFailure.unavailable}
    let lease=try LlmPackLease.resolve(store:store,selection:selection);defer{lease.close();cancellation.clear()}
    var rows=[[String:Any]]()
    for prompt in corpus.prompts{
      guard allowed() else{throw LlmFailure.cancelled}
      let loadStart=ProcessInfo.processInfo.systemUptime
      let stream=try lease.openStream(allowed:allowed,threads:2,created:{cancellation.publish($0)})
      defer{stream.close();cancellation.clear()}
      let loadMs=(ProcessInfo.processInfo.systemUptime-loadStart)*1000
      let plan=try PromptBudget.build(latest:prompt.text,count:{try stream.countTokens($0)})
      var bytes=Array(plan.text.utf8);defer{bytes.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
      let start=ProcessInfo.processInfo.systemUptime
      try bytes.withUnsafeBufferPointer{try stream.begin($0,outputLimit:256)}
      let beginMs=(ProcessInfo.processInfo.systemUptime-start)*1000
      var first:Double?,pieces=0,outputBytes=0
      while try stream.withNextPiece({piece in
        if first==nil{first=(ProcessInfo.processInfo.systemUptime-start)*1000}
        pieces+=1;outputBytes+=piece.count
      }){
        guard allowed(),pieces<=256,outputBytes<=262144 else{throw LlmFailure.unavailable}
      }
      guard allowed(),let first,pieces>0 else{throw LlmFailure.unavailable}
      rows.append(["fixture_id":prompt.id,"prompt_tokens":plan.promptTokens,"native_piece_count":pieces,"output_bytes":outputBytes,
                   "verified_open_and_load_ms":loadMs,"begin_wall_ms":beginMs,"first_native_piece_from_begin_ms":first,
                   "generation_wall_ms":(ProcessInfo.processInfo.systemUptime-start)*1000,"memory":try footprint()])
    }
    return rows
  }
}
