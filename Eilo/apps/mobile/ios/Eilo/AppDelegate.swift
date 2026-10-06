import UIKit
import AVFAudio
import React
import React_RCTAppDelegate
import ReactAppDependencyProvider

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
  // One process-owned native authority; construction never requests permission/capture.
  // No shipping trust key/origin/license approval. Installer creation is explicit and cannot auto-start capture.
  let consentAuthentication=IOSConsentAuthentication()
  let consent=NativeConsentPolicy(persistence:IOSConsentPersistence())
  let captureEffects = IOSCaptureEffects()
  let captureEligibility=IOSCaptureEligibility()
  var captureVisible: Bool { get { captureEligibility.visible } set { captureEligibility.visible=newValue } }
  lazy var conversationController = NativeController(effects:captureEffects,permission: IOSMicrophonePermission())
  func createModelStore() throws -> PackStore {
    guard let base=FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask).first else { throw PackFailure.unavailable }
    var root=base.appendingPathComponent("generic-models",isDirectory:true)
    root=try PackFiles.directory(root)
    try FileManager.default.setAttributes([.protectionKey:FileProtectionType.completeUntilFirstUserAuthentication],ofItemAtPath:root.path)
    var values=URLResourceValues();values.isExcludedFromBackup=true;try root.setResourceValues(values)
    return PackStore(root:root,trust:[:],runtime:"5e03bdd8700948b9c41c54dd1b00f28a2aebc03f",ios:ProcessInfo.processInfo.operatingSystemVersion.majorVersion)
  }
  private var audioObservers=[NSObjectProtocol]()
  var reactNativeDelegate: ReactNativeDelegate?
  var reactNativeFactory: RCTReactNativeFactory?

  func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
  ) -> Bool {
    captureEligibility.protectedData(application.isProtectedDataAvailable)
    captureEffects.eligible = { [weak self] in
      guard let self else { return false }
      return self.captureEligibility.allowed && IOSMicrophonePermission().status() == .granted
    }
    _=conversationController.setOutputGain(Float(consent.snapshot()["volume"] as? Int ?? 100)/100)
    let interruptions=AudioInterruptionHandler(conversationController)
    audioObservers.append(NotificationCenter.default.addObserver(forName:AVAudioSession.interruptionNotification,object:nil,queue:.main) { notification in
      if let type=notification.userInfo?[AVAudioSessionInterruptionTypeKey] as? UInt,type == AVAudioSession.InterruptionType.began.rawValue { interruptions.receive(.call) }
      // Interruption end never resumes; an explicit user Start is required.
    })
    for name in [AVAudioSession.mediaServicesWereLostNotification,AVAudioSession.mediaServicesWereResetNotification,Notification.Name.AVAudioEngineConfigurationChange] {
      audioObservers.append(NotificationCenter.default.addObserver(forName:name,object:nil,queue:.main) { _ in interruptions.receive(.engineReset) })
    }
    audioObservers.append(NotificationCenter.default.addObserver(forName:AVAudioSession.routeChangeNotification,object:nil,queue:.main) { [weak self] notification in
      if let reason=notification.userInfo?[AVAudioSessionRouteChangeReasonKey] as? UInt,reason == AVAudioSession.RouteChangeReason.oldDeviceUnavailable.rawValue { self?.conversationController.routeDisconnected() }
    })
    let delegate = ReactNativeDelegate()
    let factory = RCTReactNativeFactory(delegate: delegate)
    delegate.dependencyProvider = RCTAppDependencyProvider()

    reactNativeDelegate = delegate
    reactNativeFactory = factory

    return true
  }
  func applicationProtectedDataWillBecomeUnavailable(_ application: UIApplication) { consentAuthentication.cancel();captureEligibility.protectedData(false); conversationController.privacyTransition(.lock) }
  func applicationProtectedDataDidBecomeAvailable(_ application: UIApplication) { captureEligibility.protectedData(true); conversationController.privacyTransition(.unlock) }
  func applicationWillTerminate(_ application: UIApplication) { conversationController.stop() }
}

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
  var window: UIWindow?
  private var controller: NativeController? { (UIApplication.shared.delegate as? AppDelegate)?.conversationController }
  func sceneWillResignActive(_ scene: UIScene) { (UIApplication.shared.delegate as? AppDelegate)?.captureVisible=false; controller?.stop() }
  func sceneDidBecomeActive(_ scene: UIScene) { (UIApplication.shared.delegate as? AppDelegate)?.captureVisible=true; controller?.permissionChanged() }
  func sceneDidDisconnect(_ scene: UIScene) { controller?.stop() }

  func scene(
    _ scene: UIScene,
    willConnectTo session: UISceneSession,
    options connectionOptions: UIScene.ConnectionOptions
  ) {
    guard let windowScene = scene as? UIWindowScene,
      let appDelegate = UIApplication.shared.delegate as? AppDelegate,
      let factory = appDelegate.reactNativeFactory else { return }

    let sceneWindow = UIWindow(windowScene: windowScene)
    window = sceneWindow
    factory.startReactNative(withModuleName: "Eilo", in: sceneWindow, launchOptions: nil)
    sceneWindow.makeKeyAndVisible()
  }
}

class ReactNativeDelegate: RCTDefaultReactNativeFactoryDelegate {
  override func sourceURL(for bridge: RCTBridge) -> URL? {
    self.bundleURL()
  }

  override func bundleURL() -> URL? {
#if DEBUG
    RCTBundleURLProvider.sharedSettings().jsBundleURL(forBundleRoot: "index")
#else
    Bundle.main.url(forResource: "main", withExtension: "jsbundle")
#endif
  }
}
