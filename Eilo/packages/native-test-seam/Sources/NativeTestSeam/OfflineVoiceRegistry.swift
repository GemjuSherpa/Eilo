import Foundation

struct OfflineVoice: Equatable {
  let id, language: String
  let installed: Bool, networkRequired: Bool?, offlineVerified: Bool
  init(id: String, language: String, installed: Bool, networkRequired: Bool?, offlineVerified: Bool = false) {
    self.id=id;self.language=language;self.installed=installed;self.networkRequired=networkRequired;self.offlineVerified=offlineVerified
  }
}
struct OfflineVoiceSelection { let voice: OfflineVoice, epoch: UUID }
/// Platform worker refresh, bounded native snapshot. Unknown offline capability requires
/// explicit evidence for the exact installed voice/OS build; quality is no evidence.
final class OfflineVoiceRegistry {
  private let lock=NSLock()
  private var epoch=UUID(), selected:OfflineVoice?
  @discardableResult func refresh(_ voices:[OfflineVoice], requested:String?=nil)->Bool {
    lock.lock();defer{lock.unlock()};epoch=UUID();selected=nil
    guard voices.count<=128,(requested?.utf8.count ?? 0)<=256 else{return false}
    let eligible=voices.filter{v in
      v.id.range(of:"[A-Za-z0-9_.:-]{1,256}",options:.regularExpression)==v.id.startIndex..<v.id.endIndex &&
      v.language.range(of:"(?i)en(?:-[a-z0-9]{2,8})*",options:.regularExpression)==v.language.startIndex..<v.language.endIndex &&
      v.installed && (v.networkRequired == false || v.networkRequired == nil && v.offlineVerified)
    }
    guard Set(eligible.map(\.id)).count==eligible.count else{return false}
    selected=requested == nil ? eligible.sorted{$0.id<$1.id}.first:eligible.first{$0.id==requested}
    return selected != nil
  }
  func selection()->OfflineVoiceSelection?{lock.lock();defer{lock.unlock()};return selected.map{OfflineVoiceSelection(voice:$0,epoch:epoch)}}
  func current(_ value:OfflineVoiceSelection)->Bool{lock.lock();defer{lock.unlock()};return value.epoch==epoch && value.voice==selected}
  func invalidate(){lock.lock();epoch=UUID();selected=nil;lock.unlock()}
  var ready:Bool{lock.lock();defer{lock.unlock()};return selected != nil}
}
final class VoiceAwareReadiness:ModelReadinessAdapter {
  private let models:any ModelReadinessAdapter,voices:OfflineVoiceRegistry
  init(models:any ModelReadinessAdapter,voices:OfflineVoiceRegistry){self.models=models;self.voices=voices}
  func status()->ModelStatus{let status=models.status();return status != .ready ? status:(voices.ready ? .ready:.offlineVoiceMissing)}
}
