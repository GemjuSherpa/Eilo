import Foundation
import CryptoKit
#if canImport(CEiloTrialResidency) && canImport(CEiloTrialMetrics) && EILO_RESIDENT_COMPARISON
import CEiloTrialResidency
import CEiloTrialMetrics
#endif

enum TrialResidentFailure:Error,Equatable{case thermalLimit,cleanup}
enum TrialResidentDiagnostic {
  static var available:Bool {
    #if canImport(CEiloTrialResidency) && canImport(CEiloTrialMetrics) && EILO_RESIDENT_COMPARISON
    return true
    #else
    return false
    #endif
  }
  private struct Corpus:Decodable{struct Prompt:Decodable{let id,text:String};let prompts:[Prompt]}
  static func run(assets:URL,store:PackStore,selections:[LlmPackSelection],cancellation:TrialModelCancellation,allowed:@escaping()->Bool,progress:([[String:Any]],String)->Void)throws->[[String:Any]]{
    #if canImport(CEiloTrialResidency) && canImport(CEiloTrialMetrics) && EILO_RESIDENT_COMPARISON
    let expected=[("c0efea3254c2363a9559e32ac76e9987aff3a68c31b84a3e65c12aa5c01bd120",Int64(1282439424)),("9b1a69f90cc7b7404ffeabd12f58391a6323ea08ae6e517f6cfd56bbb2caf5ca",Int64(484219808))]
    guard available,allowed(),selections.count==2,zip(selections,expected).allSatisfy({$0.0.model.sha256==$0.1.0 && $0.0.model.bytes==$0.1.1}) else{throw LlmFailure.unavailable}
    let data=try Data(contentsOf:assets.appendingPathComponent("model-comparison-fixtures.json"))
    guard SHA256.hash(data:data).map({String(format:"%02x",$0)}).joined()==TrialModelDiagnostic.fixtureDigest else{throw LlmFailure.unavailable}
    let corpus=try JSONDecoder().decode(Corpus.self,from:data)
    guard corpus.prompts.map({$0.id})==(1...6).map({String(format:"compare-%02d",$0)}) else{throw LlmFailure.unavailable}
    var rows=[[String:Any]]()
    for group in TrialResidentSchedule.groups{
      let coolingStart=ProcessInfo.processInfo.systemUptime
      var before=TrialPhaseDiagnostic.environment()
      while before["thermal_state"] as? Int != 0{
        guard allowed(),ProcessInfo.processInfo.systemUptime-coolingStart<300 else{throw TrialResidentFailure.thermalLimit}
        progress(rows,"Waiting for nominal thermal state before group \(group.index)/12. No inference or audio.")
        Thread.sleep(forTimeInterval:5);before=TrialPhaseDiagnostic.environment()
      }
      let coolingMs=(ProcessInfo.processInfo.systemUptime-coolingStart)*1000
      guard allowed(),eilo_trial_residency_begin(Int32(group.candidate))==1 else{throw LlmFailure.unavailable}
      do{
        let lease=try LlmPackLease.resolve(store:store,selection:selections[group.candidate]);defer{lease.close()}
        let prompt=corpus.prompts.first{$0.id==group.fixture}!
        for repetition in 0...2{
          guard allowed() else{throw LlmFailure.cancelled}
          let environment=repetition==0 ? before:TrialPhaseDiagnostic.environment()
          guard let thermal=environment["thermal_state"] as? Int,thermal<2 else{throw TrialResidentFailure.thermalLimit}
          let start=ProcessInfo.processInfo.systemUptime
          let stream=try lease.openStream(allowed:allowed,threads:2,created:{cancellation.publish($0)})
          defer{stream.close();cancellation.clear()}
          let verifiedOpenMs=(ProcessInfo.processInfo.systemUptime-start)*1000
          let plan=try PromptBudget.build(latest:prompt.text,count:{try stream.countTokens($0)})
          var bytes=Array(plan.text.utf8);defer{bytes.withUnsafeMutableBufferPointer{$0.initialize(repeating:0)}}
          try bytes.withUnsafeBufferPointer{try stream.begin($0,outputLimit:256)}
          var pieces=0,outputBytes=0
          while try stream.withNextPiece({piece in pieces+=1;outputBytes+=piece.count}){
            guard allowed(),pieces<=256,outputBytes<=262144 else{throw LlmFailure.unavailable}
          }
          var values=[Double](repeating:0,count:7),stats=[Int32](repeating:0,count:5)
          guard allowed(),pieces>0,values.withUnsafeMutableBufferPointer({eilo_trial_phase_metrics($0.baseAddress,Int32($0.count))})==1,
            stats.withUnsafeMutableBufferPointer({eilo_trial_residency_stats($0.baseAddress,Int32($0.count))})==1,
            stats==[1,Int32(repetition+1),1,0,Int32(group.candidate)],values.allSatisfy({$0.isFinite && $0>=0}),
            values[5]>=values[1]+values[2]+values[3]+values[4],values[6]>=values[5],repetition==0 || values[0]==0 else{throw LlmFailure.unavailable}
          rows.append(["fixture_id":group.fixture,"group_index":group.index,"candidate_index":group.candidate,"repetition":repetition,"sample_index":rows.count+1,
                       "condition":repetition==0 ? "MODEL_UNLOADED":"MODEL_WEIGHTS_RESIDENT","prompt_tokens":plan.promptTokens,"native_piece_count":pieces,"output_bytes":outputBytes,
                       "verified_open_and_load_ms":verifiedOpenMs,"sample_wall_ms":(ProcessInfo.processInfo.systemUptime-start)*1000,
                       "cooldown_before_group_ms":repetition==0 ? coolingMs:0,"native_phases":Dictionary(uniqueKeysWithValues:zip(TrialPhaseDiagnostic.keys,values)),
                       "residency":["vendor_model_loads":stats[0],"generation_loads":stats[1],"resident_models":stats[2],"live_handles":stats[3],"candidate_index":stats[4]],
                       "environment_before":environment,"environment_after":TrialPhaseDiagnostic.environment(),"memory":try TrialModelDiagnostic.footprint()])
          progress(rows,"Resident comparison: \(rows.count)/36 samples. No audio.")
        }
        guard eilo_trial_residency_end()==1 else{throw TrialResidentFailure.cleanup}
      }catch{
        cancellation.clear()
        guard eilo_trial_residency_end()==1 else{throw TrialResidentFailure.cleanup}
        throw error
      }
    }
    return rows
    #else
    throw LlmFailure.unavailable
    #endif
  }
}
