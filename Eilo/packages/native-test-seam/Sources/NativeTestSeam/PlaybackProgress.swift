import Foundation
/// SDK events are metadata, never evidence that a person heard the output.
struct PlaybackProgress:Equatable {
  let clauseID:UUID
  var produced=true,queued=true,sdkStarted=false,sdkFinished=false,interruptionRequested=false,sdkInterrupted=false,failed=false,discardedBeforeStart=false
}
/// Controller-confined volatile metadata. No text/audio/wall clock/persistence.
final class PlaybackLedger {
  private var records:[PlaybackProgress]=[]
  func produced(_ id:UUID){if records.count==32{records.removeFirst()};records.append(PlaybackProgress(clauseID:id))}
  func event(_ id:UUID,_ event:OfflineSpeechEvent){update(id){switch event{
    case .started:$0.sdkStarted=true
    case .finished:$0.sdkFinished=true
    case .interrupted:$0.sdkInterrupted=true
    case .failed:$0.failed=true
  }}}
  func cancel(active:UUID?,waiting:[UUID]){
    if let active{update(active){$0.interruptionRequested = !$0.sdkFinished && !$0.sdkInterrupted}}
    waiting.forEach{id in update(id){$0.discardedBeforeStart=true}}
  }
  private func update(_ id:UUID,_ change:(inout PlaybackProgress)->Void){if let i=records.firstIndex(where:{$0.clauseID==id}){change(&records[i])}}
  func snapshot()->[PlaybackProgress]{records}
  func clear(){records.removeAll()}
}
