import Foundation
import UIKit
@objc(EiloControlHost) final class EiloControlHost:NSObject {
  private var previous="";private var revision:UInt64=0
  private var app:AppDelegate? { UIApplication.shared.delegate as? AppDelegate }
  @objc func snapshot() -> String {
    guard let c=app?.conversationController else { return "{}" }
    c.permissionChanged()
    var value:[String:Any] = ["version":1,"controller":c.snapshot(),"capturePending":c.captureIsPending,"speakerConfirmationRequired":c.speakerConfirmationRequired,"preferences":app?.consent.snapshot() ?? [:]]
    guard let raw=try? JSONSerialization.data(withJSONObject:value,options:.sortedKeys),let encoded=String(data:raw,encoding:.utf8) else { return "{}" }
    if encoded != previous { revision += 1;previous=encoded }
    value["revision"]=revision
    guard let data=try? JSONSerialization.data(withJSONObject:value,options:.sortedKeys),let result=String(data:data,encoding:.utf8) else { return "{}" }
    return result
  }
  @objc func background(_ value:String,completion:@escaping (String)->Void) {
    guard let app,app.captureEligibility.allowed,value=="true" || value=="false" else { completion(snapshot());return }
    app.conversationController.stop()
    if value=="false" { _=app.consent.chooseBackground(false,authenticated:false);completion(snapshot());return }
    let expected=app.conversationController.snapshot()["privacyEpoch"] as? UInt64
    app.consentAuthentication.request { [weak self,weak app] authenticated in
      guard let self,let app else { completion("{}");return }
      if authenticated,app.captureEligibility.allowed,app.conversationController.snapshot()["privacyEpoch"] as? UInt64 == expected { _=app.consent.chooseBackground(true,authenticated:true) }
      completion(self.snapshot())
    }
  }
  @objc func command(_ name:String,value:String) -> String {
    guard let app else { return "{}" }
    if name=="presentationReady",value.utf8.count<=256 {
      let c=app.conversationController,meta=app.conversationController.snapshot()
      let tuple:[Any]=[meta["sessionId"] ?? "",meta["operationId"] ?? "",meta["generation"] ?? 0,meta["privacyEpoch"] ?? 0]
      guard app.captureEligibility.allowed,c.token == nil,
        let expected=try? JSONSerialization.data(withJSONObject:tuple),value.data(using:.utf8)==expected else{return "{}"}
      for scene in UIApplication.shared.connectedScenes where scene.activationState == .foregroundActive {
        (scene.delegate as? SceneDelegate)?.revealClearedPresentation()
      }
      return snapshot()
    }
    if name=="presentation",value.isEmpty {
      let display=app.consent.snapshot()["display"] as? [String:Bool] ?? [:]
      let allowed=app.captureEligibility.allowed && display["text"]==true && display["voiceOnly"]==false
      app.conversationController.setSpokenPresentationEnabled(allowed)
      let result=app.conversationController.spokenPresentation(allowed:allowed)
      guard let bytes=try? JSONSerialization.data(withJSONObject:result,options:.sortedKeys),bytes.count<=32768 else{return "{}"}
      return String(data:bytes,encoding:.utf8) ?? "{}"
    }
    if name.utf8.count>32 || value.utf8.count>8 { return "{}" }
    if name != "history" && name != "volume" && name != "privateSession" && !["displayText","displayImages","displayVideo","voiceOnly"].contains(name) && !value.isEmpty { return "{}" }
    switch name {
    case "displayText","displayImages","displayVideo","voiceOnly":
      guard value=="true" || value=="false",app.consent.chooseDisplay(name,enabled:value=="true",authorized:app.captureEligibility.allowed) else { return "{}" }
      let display=app.consent.snapshot()["display"] as? [String:Bool] ?? [:]
      app.conversationController.setSpokenPresentationEnabled(app.captureEligibility.allowed && display["text"]==true && display["voiceOnly"]==false)
    case "privateSession":
      guard value=="true",app.captureEligibility.allowed else { return snapshot() }
      app.conversationController.privacyTransition(.privateSession)
      _=app.consent.choosePrivateSession(true)
    case "volume":
      guard app.captureEligibility.allowed,let level=Int(value),(0...100).contains(level) else { return "{}" }
      let before=app.consent.snapshot()["volume"] as? Int ?? 100
      guard app.conversationController.setOutputGain(Float(level)/100) else { return "{}" }
      guard app.consent.chooseVolume(level) else { app.conversationController.setOutputGain(Float(before)/100);return "{}" }
    case "history":
      guard app.captureEligibility.allowed,let choice=HistoryChoice(rawValue:value),choice != .unselected else { return "{}" }
      app.conversationController.privacyTransition(.privateSession)
      guard app.consent.chooseHistory(choice) else { return "{}" }
    case "completeOnboarding": guard app.captureEligibility.allowed,app.consent.completeOnboarding() else { return "{}" }
    case "stop": app.conversationController.stop()
    case "start": if app.captureEligibility.allowed && app.consent.canStart { app.conversationController.dispatch(.start) }
    case "confirmSpeaker": if app.captureEligibility.allowed { app.conversationController.confirmSpeaker() }
    default: return "{}"
    }
    return snapshot()
  }
}
