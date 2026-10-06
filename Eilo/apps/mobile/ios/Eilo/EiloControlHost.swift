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
  @objc func command(_ name:String,value:String) -> String {
    guard let app else { return "{}" }
    if name != "history" && !value.isEmpty { return "{}" }
    switch name {
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
