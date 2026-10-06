package com.eilo

import com.facebook.react.ReactActivity
import com.facebook.react.ReactActivityDelegate
import com.facebook.react.defaults.DefaultNewArchitectureEntryPoint.fabricEnabled
import com.facebook.react.defaults.DefaultReactActivityDelegate

class MainActivity : ReactActivity() {
  private var consentConfirmation:((Boolean)->Unit)?=null
  fun authenticateConsent(completion:(Boolean)->Unit) {
    val manager=getSystemService(android.app.KeyguardManager::class.java)
    if(consentConfirmation!=null || !manager.isDeviceSecure || isFinishing || isDestroyed) { completion(false);return }
    val intent=manager.createConfirmDeviceCredentialIntent("Confirm Eilo setting","Unlock to change your local consent choice")
    if(intent==null) { completion(false);return }
    consentConfirmation=completion
    try { startActivityForResult(intent,2811) } catch (_:Exception) { consentConfirmation=null;completion(false) }
  }
  override fun onActivityResult(requestCode:Int,resultCode:Int,data:android.content.Intent?) {
    super.onActivityResult(requestCode,resultCode,data)
    if(requestCode==2811) { val completion=consentConfirmation;consentConfirmation=null;android.os.Handler(android.os.Looper.getMainLooper()).post { completion?.invoke(resultCode==RESULT_OK) } }
  }
  private val controller get() = (application as MainApplication).conversationController
  override fun onCreate(savedInstanceState: android.os.Bundle?) {
    supportFragmentManager.fragmentFactory = com.swmansion.rnscreens.fragment.restoration.RNScreensFragmentFactory()
    super.onCreate(savedInstanceState)
    controller.bindPermissionAdapter(com.eilo.foundation.AndroidMicrophonePermission(this))
  }
  override fun onResume() { super.onResume(); (application as MainApplication).foregroundCaptureVisible=true; controller.permissionChanged() }
  // Foreground-only: exit cancels pending opens and releases native capture.
  override fun onPause() { (application as MainApplication).foregroundCaptureVisible=false; controller.stop(); super.onPause() }
  override fun onDestroy() {
    consentConfirmation?.invoke(false);consentConfirmation=null
    controller.bindPermissionAdapter(com.eilo.foundation.UnavailablePermissionAdapter())
    super.onDestroy()
  }


  /**
   * Returns the name of the main component registered from JavaScript. This is used to schedule
   * rendering of the component.
   */
  override fun getMainComponentName(): String = "Eilo"

  /**
   * Returns the instance of the [ReactActivityDelegate]. We use [DefaultReactActivityDelegate]
   * which allows you to enable New Architecture with a single boolean flags [fabricEnabled]
   */
  override fun createReactActivityDelegate(): ReactActivityDelegate =
      DefaultReactActivityDelegate(this, mainComponentName, fabricEnabled)
}
