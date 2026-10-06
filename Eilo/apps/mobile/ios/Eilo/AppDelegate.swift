import UIKit
import React
import React_RCTAppDelegate
import ReactAppDependencyProvider

@main
class AppDelegate: UIResponder, UIApplicationDelegate {
  // One process-owned native authority; construction never requests permission/capture.
  // No shipping trust key/origin/license approval. Installer creation is explicit and cannot auto-start capture.
  let conversationController = NativeController(permission: IOSMicrophonePermission())
  func createModelStore() throws -> PackStore {
    guard let base=FileManager.default.urls(for:.applicationSupportDirectory,in:.userDomainMask).first else { throw PackFailure.unavailable }
    var root=base.appendingPathComponent("generic-models",isDirectory:true)
    try FileManager.default.createDirectory(at:root,withIntermediateDirectories:true,attributes:[.protectionKey:FileProtectionType.completeUntilFirstUserAuthentication])
    var values=URLResourceValues();values.isExcludedFromBackup=true;try root.setResourceValues(values)
    return PackStore(root:root,trust:[:],runtime:"5e03bdd8700948b9c41c54dd1b00f28a2aebc03f",ios:ProcessInfo.processInfo.operatingSystemVersion.majorVersion)
  }
  var reactNativeDelegate: ReactNativeDelegate?
  var reactNativeFactory: RCTReactNativeFactory?

  func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]? = nil
  ) -> Bool {
    let delegate = ReactNativeDelegate()
    let factory = RCTReactNativeFactory(delegate: delegate)
    delegate.dependencyProvider = RCTAppDependencyProvider()

    reactNativeDelegate = delegate
    reactNativeFactory = factory

    return true
  }
  func applicationProtectedDataWillBecomeUnavailable(_ application: UIApplication) { conversationController.privacyTransition(.lock) }
  func applicationProtectedDataDidBecomeAvailable(_ application: UIApplication) { conversationController.privacyTransition(.unlock) }
  func applicationWillTerminate(_ application: UIApplication) { conversationController.stop() }
}

class SceneDelegate: UIResponder, UIWindowSceneDelegate {
  var window: UIWindow?
  private var controller: NativeController? { (UIApplication.shared.delegate as? AppDelegate)?.conversationController }
  func sceneWillResignActive(_ scene: UIScene) { controller?.stop() }
  func sceneDidBecomeActive(_ scene: UIScene) { controller?.permissionChanged() }
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
