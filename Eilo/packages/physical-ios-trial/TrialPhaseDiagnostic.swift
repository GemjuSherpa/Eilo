import Foundation
import CryptoKit
import UIKit
#if canImport(CEiloTrialMetrics) && EILO_PHASE_MEASUREMENTS
import CEiloTrialMetrics
#endif

/// Fresh handle per prompt, three rounds; no resident-model or filesystem-cache claim.
enum TrialPhaseDiagnostic {
  static var available:Bool {
    #if canImport(CEiloTrialMetrics) && EILO_PHASE_MEASUREMENTS
    return true
    #else
    return false
    #endif
  }
  static let keys=["model_load_ms","tokenize_ms","context_setup_ms","prefill_ms","first_sample_ms","begin_to_first_token_ms","begin_to_first_piece_ms"]
  private struct Corpus:Decodable{struct Prompt:Decodable{let id,text:String};let prompts:[Prompt]}
  /// UIKit battery monitoring is owned/restored by the foreground controller.
  static func environment()->[String:Any]{
    dispatchPrecondition(condition:.notOnQueue(.main))
    return DispatchQueue.main.sync {
      let device=UIDevice.current,level=device.batteryLevel
      let battery:Any = level>=0 && level<=1 ? Double(level) : NSNull()
      return ["battery_level":battery,"battery_state":device.batteryState.rawValue,
              "thermal_state":ProcessInfo.processInfo.thermalState.rawValue,
              "low_power_mode":ProcessInfo.processInfo.isLowPowerModeEnabled,
              "system_uptime_s":ProcessInfo.processInfo.systemUptime]
    }
  }
  static func run(assets:URL,store:PackStore,selection:LlmPackSelection,cancellation:TrialModelCancellation,allowed:@escaping()->Bool,progress:([[String:Any]])->Void)throws->[[String:Any]]{
    #if canImport(CEiloTrialMetrics) && EILO_PHASE_MEASUREMENTS
    guard available,allowed() else{throw LlmFailure.unavailable}
    let data=try Data(contentsOf:assets.appendingPathComponent("model-comparison-fixtures.json"))
    guard SHA256.hash(data:data).map({String(format:"%02x",$0)}).joined()==TrialModelDiagnostic.fixtureDigest else{throw LlmFailure.unavailable}
    let corpus=try JSONDecoder().decode(Corpus.self,from:data)
    guard corpus.prompts.map({$0.id})==(1...6).map({String(format:"compare-%02d",$0)}) else{throw LlmFailure.unavailable}
    let lease=try LlmPackLease.resolve(store:store,selection:selection);defer{lease.close();cancellation.clear()}
    var rows=[[String:Any]]()
    for round in 1...3{
      for prompt in corpus.prompts{
        guard allowed() else{throw LlmFailure.cancelled}
        let before=environment(),start=ProcessInfo.processInfo.systemUptime
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
        var values=[Double](repeating:0,count:7)
        guard allowed(),pieces>0,values.withUnsafeMutableBufferPointer({eilo_trial_phase_metrics($0.baseAddress,Int32($0.count))})==1,
          values.allSatisfy({$0.isFinite && $0>=0}),values[5]>=values[1]+values[2]+values[3]+values[4],values[6]>=values[5] else{throw LlmFailure.unavailable}
        rows.append(["fixture_id":prompt.id,"round":round,"sample_index":rows.count+1,"prompt_tokens":plan.promptTokens,
                     "native_piece_count":pieces,"output_bytes":outputBytes,"verified_open_and_load_ms":verifiedOpenMs,
                     "sample_wall_ms":(ProcessInfo.processInfo.systemUptime-start)*1000,
                     "native_phases":Dictionary(uniqueKeysWithValues:zip(keys,values)),"environment_before":before,
                     "environment_after":environment(),"memory":try TrialModelDiagnostic.footprint()])
        progress(rows)
      }
    }
    return rows
    #else
    throw LlmFailure.unavailable
    #endif
  }
}
